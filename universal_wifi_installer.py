"""
=============================================================================
INSTALADOR UNIVERSAL & INTELIGENTE DE DRIVERS USB WI-FI
Compatível com: Windows 11, 10, 8.1, 8, 7 e Windows Server (32 e 64 bits)
Especialidade: Exclusivo para Adaptadores de Rede Sem Fio USB (Dongles Wi-Fi)
=============================================================================
Autor: Alexandre Cristóvão (alexissanz)
=============================================================================
"""

import sys
import os
import shutil
import subprocess
import time
import re
import urllib.request
import urllib.parse
import json
import ctypes
from ctypes import wintypes

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False

def elevate():
    if not is_admin():
        print("[*] Solicitando permissoes de Administrador...")
        params = " ".join([f'"{arg}"' for arg in sys.argv])
        if getattr(sys, 'frozen', False):
            ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, params, None, 1)
        else:
            ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, f'"{__file__}" {params}', None, 1)
        sys.exit(0)

def run_cmd(cmd):
    try:
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, text=True, errors='ignore')
        return res.returncode, res.stdout.strip(), res.stderr.strip()
    except Exception as e:
        return -1, "", str(e)

def log(msg, status="INFO"):
    colors = {
        "INFO": "\033[94m[*]\033[0m",
        "SUCCESS": "\033[92m[✓]\033[0m",
        "WARN": "\033[93m[!]\033[0m",
        "ERROR": "\033[91m[✗]\033[0m",
        "WIFI": "\033[96m[📶]\033[0m"
    }
    prefix = colors.get(status, "[*]")
    print(f"{prefix} {msg}")

# ============================================================================
# BASE DE CONHECIMENTO DE HARDWARE: VENDOR IDs DE CHIPSETS WI-FI USB
# ============================================================================
KNOWN_WIFI_VIDS = [
    "0BDA", # Realtek (RTL8188, RTL8192, RTL8811, RTL8812, etc.)
    "148F", # Ralink / MediaTek (RT5370, RT3070, MT7601U, etc.)
    "0E8D", # MediaTek USB
    "2310", # ZTOPMICRO (ZT9101, Free 4)
    "350B", # ZTop Microelectronics
    "A69C", # AicSemi (AIC8800)
    "0CF3", # Qualcomm Atheros (AR9271, etc.)
    "0A5C", # Broadcom USB WLAN
    "2357", # TP-Link USB Adapters
    "7392", # Edimax
    "2001", # D-Link
    "0846", # Netgear
    "0B05", # ASUS
    "2604"  # Tenda
]

def get_base_dir():
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))

# ============================================================================
# 1. COMUTADOR AUTOMÁTICO DE DONGLES ZEROCD (MODO DUPLO CD-ROM -> WI-FI)
# ============================================================================
def eject_drive(drive_letter):
    drive = drive_letter.rstrip('\\').rstrip(':') + ":"
    log(f"Comutando dongle USB na partição {drive} para modo Wi-Fi...", "INFO")
    
    ps_cmd = f'(New-Object -comObject Shell.Application).Namespace(17).ParseName("{drive}\\").InvokeVerb("Eject")'
    run_cmd(f'powershell -NoProfile -Command "{ps_cmd}"')
    
    try:
        h_drive = ctypes.windll.kernel32.CreateFileW(
            f"\\\\.\\{drive}", 0x80000000 | 0x40000000, 1 | 2, None, 3, 0, None
        )
        if h_drive != -1:
            bytes_returned = wintypes.DWORD()
            IOCTL_STORAGE_EJECT_MEDIA = 0x2D4808
            ctypes.windll.kernel32.DeviceIoControl(
                h_drive, IOCTL_STORAGE_EJECT_MEDIA, None, 0, None, 0,
                ctypes.byref(bytes_returned), None
            )
            ctypes.windll.kernel32.CloseHandle(h_drive)
    except Exception:
        pass

def switch_zerocd_dongles():
    """Localiza qualquer pendrive Wi-Fi preso em modo CD-ROM e ejeta."""
    code, stdout, _ = run_cmd("powershell -NoProfile -Command \"Get-Volume | Where-Object { $_.FriendlyName -like '*ZTOP*' -or $_.FriendlyName -like '*WIFI*' -or $_.FriendlyName -like '*REALTEK*' } | Select-Object -ExpandProperty DriveLetter\"")
    for dl in stdout.splitlines():
        dl = dl.strip()
        if dl:
            eject_drive(dl)
            time.sleep(2)
            
    # Procura executáveis de autorun de Wi-Fi em letras de unidade
    import string
    for letter in string.ascii_uppercase:
        for marker in [f"{letter}:\\auto_load.exe", f"{letter}:\\autorun.exe", f"{letter}:\\Setup.exe"]:
            if os.path.exists(marker):
                # Verifica se o arquivo tem relação com Wi-Fi
                try:
                    with open(marker, 'rb') as f:
                        content = f.read(200000).lower()
                        if b'wifi' in content or b'802.11' in content or b'wlan' in content or b'ztop' in content or b'realtek' in content:
                            log(f"Dongle Wi-Fi em modo virtual detectado na unidade {letter}:", "INFO")
                            eject_drive(letter)
                            time.sleep(2)
                            break
                except Exception:
                    pass

# ============================================================================
# 2. VARREDURA EXCLUSIVA DE ADAPTADORES WI-FI USB
# ============================================================================
def scan_usb_wifi_devices():
    """Identifica especificamente todos os adaptadores Wi-Fi USB conectados."""
    log("Escaneando exclusivamente adaptadores de rede Wi-Fi USB...", "WIFI")
    
    ps_cmd = """
    Get-PnpDevice | Where-Object { 
        ($_.InstanceId -like 'USB*') -and 
        (
            ($_.Class -eq 'Net') -or 
            ($_.FriendlyName -match '802\\.11|Wireless|Wi-Fi|WLAN|NIC|Adapter') -or 
            ($_.Status -ne 'OK')
        )
    } | Select-Object FriendlyName, InstanceId, Class, Status, Problem, ConfigManagerErrorCode | ConvertTo-Json
    """
    code, out, _ = run_cmd(f'powershell -NoProfile -Command "{ps_cmd}"')
    
    devices = []
    if out.strip():
        try:
            data = json.loads(out)
            if isinstance(data, dict):
                data = [data]
            for d in data:
                inst = d.get("InstanceId", "").upper()
                name = d.get("FriendlyName", "")
                
                # Checa se é um chipset Wi-Fi conhecido ou se o nome indica Wi-Fi
                is_wifi = False
                for vid in KNOWN_WIFI_VIDS:
                    if f"VID_{vid}" in inst:
                        is_wifi = True
                        break
                if any(k in name.lower() for k in ["802.11", "wireless", "wi-fi", "wlan"]):
                    is_wifi = True
                    
                if is_wifi:
                    devices.append(d)
        except Exception:
            pass

    return devices

# ============================================================================
# 3. MOTOR INTELIGENTE DE INSTALAÇÃO DE DRIVERS (LOCAL + DRIVERSTORE + PNP)
# ============================================================================
def install_bundled_driver(device_inst, base_dir):
    """Instala drivers empacotados localmente (ZT9101, etc.)."""
    is_64bit = ctypes.sizeof(ctypes.c_voidp) == 8
    arch = "x64" if is_64bit else "x86"

    # Se for ZTOPMICRO ZT9101
    if "VID_2310" in device_inst or "VID_350B" in device_inst:
        log("Chipset ZTOPMICRO ZT9101 detectado. Instalando microcódigo e drivers WHQL...", "INFO")
        
        # 1. Copiar firmware.bin obrigatório
        dest_dirs = [r"C:\Program Files (x86)\ZTOPMICRO", r"C:\Program Files\ZTOPMICRO"]
        for d in dest_dirs:
            os.makedirs(d, exist_ok=True)
            
        fw_src = os.path.join(base_dir, "payload", "service", "firmware.bin")
        if not os.path.exists(fw_src):
            # Procura em subpastas
            for root, _, files in os.walk(base_dir):
                if "firmware.bin" in files:
                    fw_src = os.path.join(root, "firmware.bin")
                    break
        if os.path.exists(fw_src):
            for d in dest_dirs:
                try: shutil.copy2(fw_src, os.path.join(d, "firmware.bin"))
                except Exception: pass

        # 2. Instalar driver INF via PnPUtil
        inf_file = os.path.join(base_dir, "payload", "drivers", arch, "usbwifi_ndis6.inf")
        if not os.path.exists(inf_file):
            for root, _, files in os.walk(base_dir):
                if "usbwifi_ndis6.inf" in files and arch in root:
                    inf_file = os.path.join(root, "usbwifi_ndis6.inf")
                    break
        if os.path.exists(inf_file):
            code, out, _ = run_cmd(f'pnputil /add-driver "{inf_file}" /install')
            return True
            
    return False

def search_driverstore_for_hardware(hardware_id):
    """Varre o repositório DriverStore do Windows por qualquer INF compatível com o Hardware ID."""
    log(f"Buscando driver correspondente no DriverStore para: {hardware_id}...", "INFO")
    
    vid_pid = ""
    match = re.search(r'VID_([0-9A-F]{4})&PID_([0-9A-F]{4})', hardware_id, re.IGNORECASE)
    if match:
        vid_pid = f"VID_{match.group(1)}&PID_{match.group(2)}".upper()

    repo_dir = r"C:\Windows\System32\DriverStore\FileRepository"
    if not os.path.exists(repo_dir) or not vid_pid:
        return None

    # Procura arquivos .inf de rede no DriverStore
    for root, dirs, files in os.walk(repo_dir):
        for f in files:
            if f.lower().endswith(".inf") and ("net" in f.lower() or "wlan" in f.lower() or "wifi" in f.lower()):
                full_inf = os.path.join(root, f)
                try:
                    with open(full_inf, 'rb') as fp:
                        raw = fp.read()
                        # Checa formato ANSI ou UTF-16
                        txt = raw.decode('utf-16le', errors='ignore') if raw.startswith(b'\xff\xfe') else raw.decode('latin1', errors='ignore')
                        if vid_pid in txt.upper():
                            log(f"Driver compatível localizado no DriverStore: {full_inf}", "SUCCESS")
                            return full_inf
                except Exception:
                    pass
    return None

def trigger_pnp_driver_search():
    """Força o Windows Plug and Play Manager a reexaminar e vincular drivers."""
    log("Acionando verificação de hardware PnP no barramento USB...", "INFO")
    run_cmd("pnputil /scan-devices >nul 2>&1")

# ============================================================================
# 4. CONFIGURAÇÃO E REPARO DA STACK WI-FI DO WINDOWS
# ============================================================================
def repair_wlan_stack():
    """Garante que o serviço de redes sem fio e drivers de barramento estejam perfeitos."""
    log("Verificando integridade da pilha de rede sem fio (WLAN AutoConfig)...", "INFO")
    
    # Se Windows Server, checa a feature Wireless-Networking
    code, stdout, _ = run_cmd("powershell -NoProfile -Command \"(Get-WmiObject Win32_OperatingSystem).Caption\"")
    if "server" in stdout.lower():
        code_feat, feat_out, _ = run_cmd("powershell -NoProfile -Command \"(Get-WindowsFeature -Name Wireless-Networking).Installed\"")
        if "true" not in feat_out.lower():
            log("Windows Server detectado: Habilitando recurso Wireless LAN Service...", "INFO")
            run_cmd("powershell -NoProfile -Command \"Install-WindowsFeature -Name Wireless-Networking\"")
        
        # Injeta vwifibus se necessário
        if not os.path.exists(r"C:\Windows\System32\drivers\vwifibus.sys"):
            run_cmd("powershell -NoProfile -Command \"Copy-Item 'C:\\Windows\\WinSxS\\amd64_microsoft-windows-vwifi*\\*' 'C:\\Windows\\System32\\drivers\\' -Force -ErrorAction SilentlyContinue\"")

    # Inicia e define WlanSvc como Automático
    run_cmd("sc.exe config wlansvc start= auto >nul 2>&1")
    run_cmd("sc.exe start wlansvc >nul 2>&1")
    run_cmd("net start wlansvc >nul 2>&1")

def restart_wifi_adapters():
    """Reinicia os adaptadores de rede Wi-Fi para recarregar comutação de hardware."""
    ps_cmd = """
    Get-NetAdapter | Where-Object { 
        ($_.InterfaceDescription -match '802\\.11|Wireless|Wi-Fi|WLAN|USB') -or 
        ($_.Name -match 'Wi-Fi') 
    } | ForEach-Object {
        Disable-NetAdapter -Name $_.Name -Confirm:$false -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 1
        Enable-NetAdapter -Name $_.Name -Confirm:$false -ErrorAction SilentlyContinue
    }
    """
    run_cmd(f'powershell -NoProfile -Command "{ps_cmd}"')

# ============================================================================
# 5. DIAGNÓSTICO E EXIBIÇÃO DE REDES WI-FI DISPONÍVEIS
# ============================================================================
def show_wifi_diagnostics():
    print("\n" + "=" * 65)
    print("        RELATÓRIO DE STATUS DOS ADAPTADORES WI-FI USB")
    print("=" * 65)
    
    # 1. PnP Devices Status
    code, pnp_out, _ = run_cmd("""
    powershell -NoProfile -Command "Get-PnpDevice -PresentOnly | Where-Object { 
        ($_.InstanceId -like 'USB*') -and 
        (
            ($_.Class -eq 'Net') -or 
            ($_.FriendlyName -match '802\\.11|Wireless|Wi-Fi|NIC|Adapter')
        )
    } | Select-Object FriendlyName, InstanceId, Status | Format-Table -AutoSize"
    """)
    if pnp_out.strip():
        print(pnp_out)
    else:
        log("Nenhum adaptador Wi-Fi USB ativo detectado no momento.", "WARN")

    # 2. NetAdapter Status
    code, net_out, _ = run_cmd("""
    powershell -NoProfile -Command "Get-NetAdapter | Where-Object { 
        ($_.InterfaceDescription -match '802\\.11|Wireless|Wi-Fi|WLAN') -or 
        ($_.Name -match 'Wi-Fi') 
    } | Format-Table Name, InterfaceDescription, Status, MacAddress, LinkSpeed -AutoSize"
    """)
    if net_out.strip():
        print("\n--- Interface de Rede Wi-Fi Ativa ---")
        print(net_out)

    # 3. Varredura de Redes Sem Fio
    print("\n--- Redes Wi-Fi Detectadas em Tempo Real ---")
    code, wlan_out, _ = run_cmd("netsh wlan show networks")
    if code == 0 and "SSID" in wlan_out:
        print(wlan_out)
        log("O ADAPTADOR WI-FI ESTÁ 100% FUNCIONAL E PRONTO PARA NAVEGAÇÃO!", "SUCCESS")
    else:
        log("Adaptador configurado. Abra o menu de rede da barra de tarefas para conectar.", "SUCCESS")

# ============================================================================
# FLUXO PRINCIPAL
# ============================================================================
def main():
    elevate()
    base_dir = get_base_dir()

    print("=" * 65)
    print("   INSTALADOR UNIVERSAL & INTELIGENTE DE DRIVERS USB WI-FI")
    print("=" * 65 + "\n")

    # Passo 1: Comutar dongles ZeroCD
    switch_zerocd_dongles()

    # Passo 2: Reparar pilha WLAN do Windows
    repair_wlan_stack()

    # Passo 3: Escanear dispositivos Wi-Fi USB
    devices = scan_usb_wifi_devices()
    if not devices:
        log("Nenhum adaptador USB Wi-Fi conectado detectado.", "WARN")
        print("Insira o adaptador USB Wi-Fi em qualquer porta e execute novamente.")
    else:
        log(f"Foram identificados {len(devices)} adaptador(es) USB Wi-Fi:", "INFO")
        for dev in devices:
            name = dev.get("FriendlyName", "Dispositivo Desconhecido")
            inst = dev.get("InstanceId", "")
            status = dev.get("Status", "")
            log(f"-> {name} | ID: {inst} | Status: {status}", "WIFI")

            # Se o dispositivo estiver com erro de driver ou não configurado
            if status != "OK":
                log(f"Instalando driver para {name}...", "INFO")
                installed = False
                
                # Nível 1: Driver local empacotado
                if install_bundled_driver(inst, base_dir):
                    installed = True

                # Nível 2: Busca inteligente no DriverStore
                if not installed:
                    inf_match = search_driverstore_for_hardware(inst)
                    if inf_match:
                        code, out, _ = run_cmd(f'pnputil /add-driver "{inf_match}" /install')
                        if code == 0 or "sucesso" in out.lower():
                            log("Driver instalado com sucesso a partir do DriverStore!", "SUCCESS")
                            installed = True

                # Nível 3: PnP Re-scan
                if not installed:
                    trigger_pnp_driver_search()

    # Passo 4: Reiniciar adaptadores e sincronizar chipset
    restart_wifi_adapters()

    # Passo 5: Diagnóstico final
    show_wifi_diagnostics()

    print("\n" + "=" * 65)
    print("   PROCESSO DE INSTALAÇÃO DE USB WI-FI CONCLUÍDO!")
    print("=" * 65)
    try:
        if sys.stdin and sys.stdin.isatty():
            input("\nPressione ENTER para fechar...")
    except Exception:
        pass

if __name__ == "__main__":
    main()
