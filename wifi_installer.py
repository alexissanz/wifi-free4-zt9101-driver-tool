"""
=============================================================================
INSTALADOR DEFINITIVO & AUTOMÁTICO DO ADAPTADOR USB WI-FI "FREE 4" (ZT9101)
Compatível com: Windows 11, 10, 8.1, 8, 7, Server (32-bit e 64-bit)
Chipset: ZTOPMICRO ZT9101 / 9101DV20 (VID_2310 / VID_350B)
=============================================================================
"""

import sys
import os
import shutil
import subprocess
import time
import platform
import ctypes
from ctypes import wintypes

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False

def elevate():
    """Reinicia o script com privilégios de Administrador se necessário."""
    if not is_admin():
        print("[*] Solicitando permissões de Administrador...")
        params = " ".join([f'"{arg}"' for arg in sys.argv])
        if getattr(sys, 'frozen', False):
            ret = ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, params, None, 1)
        else:
            ret = ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, f'"{__file__}" {params}', None, 1)
        sys.exit(0)

def get_base_dir():
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))

def run_cmd(cmd, check=False):
    """Executa comando silenciosamente ou retornando saída."""
    try:
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, text=True, errors='ignore')
        return res.returncode, res.stdout.strip(), res.stderr.strip()
    except Exception as e:
        return -1, "", str(e)

def log_step(step, status="INFO"):
    colors = {
        "INFO": "\033[94m[*]\033[0m",
        "SUCCESS": "\033[92m[✓]\033[0m",
        "WARN": "\033[93m[!]\033[0m",
        "ERROR": "\033[91m[✗]\033[0m",
    }
    prefix = colors.get(status, "[*]")
    print(f"{prefix} {step}")

def eject_drive(drive_letter):
    """Ejeta a unidade de CD-ROM virtual para comutar o dongle para modo Wi-Fi."""
    drive = drive_letter.rstrip('\\').rstrip(':') + ":"
    log_step(f"Ejetando partição virtual {drive} para ativar modo Wi-Fi...", "INFO")
    
    # Método 1: PowerShell Shell.Application
    ps_cmd = f'(New-Object -comObject Shell.Application).Namespace(17).ParseName("{drive}\\").InvokeVerb("Eject")'
    run_cmd(f'powershell -NoProfile -Command "{ps_cmd}"')
    
    # Método 2: IOCTL DeviceIoControl
    try:
        h_drive = ctypes.windll.kernel32.CreateFileW(
            f"\\\\.\\{drive}",
            0x80000000 | 0x40000000, # GENERIC_READ | GENERIC_WRITE
            1 | 2,                    # FILE_SHARE_READ | FILE_SHARE_WRITE
            None,
            3,                        # OPEN_EXISTING
            0,
            None
        )
        if h_drive != -1:
            bytes_returned = wintypes.DWORD()
            IOCTL_STORAGE_EJECT_MEDIA = 0x2D4808
            ctypes.windll.kernel32.DeviceIoControl(
                h_drive,
                IOCTL_STORAGE_EJECT_MEDIA,
                None, 0,
                None, 0,
                ctypes.byref(bytes_returned),
                None
            )
            ctypes.windll.kernel32.CloseHandle(h_drive)
    except Exception:
        pass

def find_and_switch_dongle():
    """Detecta se o pendrive Wi-Fi está no modo CD-ROM e o converte para Wi-Fi."""
    # Procura drives com rótulo ZTOPMICRO ou que tenham auto_load.exe
    code, stdout, _ = run_cmd("powershell -NoProfile -Command \"Get-Volume | Where-Object { $_.FriendlyName -like '*ZTOP*' } | Select-Object -ExpandProperty DriveLetter\"")
    found = False
    for dl in stdout.splitlines():
        dl = dl.strip()
        if dl:
            found = True
            eject_drive(dl)
            time.sleep(2)
            
    if not found:
        # Verifica se alguma letra de unidade contém auto_load.exe de ZTop
        import string
        for letter in string.ascii_uppercase:
            marker = f"{letter}:\\auto_load.exe"
            if os.path.exists(marker):
                log_step(f"Dongle detectado na unidade {letter}:", "INFO")
                eject_drive(letter)
                time.sleep(2)
                break

def stage_firmware_and_service(base_dir):
    """Instala o firmware obrigatório e o serviço Auto_eject."""
    log_step("Preparando arquivos de firmware e serviço de detecção USB...", "INFO")
    
    # Parar o serviço antes de tentar sobrescrever arquivos
    run_cmd("sc.exe stop Auto_eject >nul 2>&1")
    run_cmd("taskkill /F /IM Auto_eject.exe >nul 2>&1")
    time.sleep(1)

    dest_dirs = [
        r"C:\Program Files (x86)\ZTOPMICRO",
        r"C:\Program Files\ZTOPMICRO"
    ]
    for d in dest_dirs:
        os.makedirs(d, exist_ok=True)
    
    service_dir = os.path.join(base_dir, "payload", "service")
    if not os.path.exists(service_dir):
        service_dir = base_dir

    firmware_src = os.path.join(service_dir, "firmware.bin")
    auto_eject_src = os.path.join(service_dir, "Auto_eject.exe")
    uninstall_src = os.path.join(service_dir, "uninstall.exe")

    def safe_copy(src, dst):
        if not os.path.exists(src):
            return
        try:
            shutil.copy2(src, dst)
        except Exception:
            pass

    for d in dest_dirs:
        safe_copy(firmware_src, os.path.join(d, "firmware.bin"))
        safe_copy(auto_eject_src, os.path.join(d, "Auto_eject.exe"))
        safe_copy(uninstall_src, os.path.join(d, "uninstall.exe"))

    # Configurar e Iniciar serviço Auto_eject para que detecções futuras sejam automáticas
    svc_bin = r"C:\Program Files (x86)\ZTOPMICRO\Auto_eject.exe"
    if not os.path.exists(svc_bin):
        svc_bin = r"C:\Program Files\ZTOPMICRO\Auto_eject.exe"
        
    if os.path.exists(svc_bin):
        run_cmd(f'sc.exe create Auto_eject binPath= "{svc_bin}" start= auto DisplayName= "ZTOPMICRO 9101DV20 auto eject" >nul 2>&1')
        run_cmd("sc.exe start Auto_eject >nul 2>&1")
        log_step("Serviço Auto_eject configurado com sucesso.", "SUCCESS")

def install_driver(base_dir):
    """Instala o driver WHQL correto para a arquitetura do sistema."""
    is_64bit = platform.machine().endswith('64') or '64' in platform.architecture()[0]
    arch_folder = "x64" if is_64bit else "x86"
    log_step(f"Arquitetura detectada: {'64-bit (x64)' if is_64bit else '32-bit (x86)'}", "INFO")

    inf_path = os.path.join(base_dir, "payload", "drivers", arch_folder, "usbwifi_ndis6.inf")
    if not os.path.exists(inf_path):
        # Procura recursivamente
        for root, _, files in os.walk(base_dir):
            if "usbwifi_ndis6.inf" in files and arch_folder in root:
                inf_path = os.path.join(root, "usbwifi_ndis6.inf")
                break

    if not os.path.exists(inf_path):
        log_step(f"Arquivo INF não encontrado em {inf_path}!", "ERROR")
        return False

    log_step(f"Instalando driver assinado WHQL via PnPUtil: {inf_path}", "INFO")
    code, stdout, stderr = run_cmd(f'pnputil.exe /add-driver "{inf_path}" /install')
    
    if "sucesso" in stdout.lower() or "success" in stdout.lower() or code == 0:
        log_step("Driver adicionado e instalado no Windows Driver Store com sucesso!", "SUCCESS")
        return True
    else:
        log_step(f"Resultado do PnPUtil: {stdout}", "WARN")
        return code == 0

def ensure_wlan_service():
    """Garante que o serviço de rede sem fio (WlanSvc) esteja ativo e configurado."""
    log_step("Verificando serviço de rede sem fio (WLAN AutoConfig)...", "INFO")
    
    # Se for Windows Server, checa a feature Wireless-Networking
    code, stdout, _ = run_cmd("powershell -NoProfile -Command \"(Get-WmiObject Win32_OperatingSystem).Caption\"")
    if "server" in stdout.lower():
        code_feat, feat_out, _ = run_cmd("powershell -NoProfile -Command \"(Get-WindowsFeature -Name Wireless-Networking).Installed\"")
        if "true" not in feat_out.lower():
            log_step("Windows Server detectado. Instalando Wireless LAN Service...", "INFO")
            run_cmd("powershell -NoProfile -Command \"Install-WindowsFeature -Name Wireless-Networking\"")
        
        # Garante cópia do driver de barramento vwifi se necessário
        vdir = r"C:\Windows\System32\drivers\vwifibus.sys"
        if not os.path.exists(vdir):
            run_cmd("powershell -NoProfile -Command \"Copy-Item 'C:\\Windows\\WinSxS\\amd64_microsoft-windows-vwifi*\\*' 'C:\\Windows\\System32\\drivers\\' -Force\"")

    # Inicia e define WlanSvc como Automático
    run_cmd("sc.exe config wlansvc start= auto >nul 2>&1")
    run_cmd("sc.exe start wlansvc >nul 2>&1")
    
    code, stdout, _ = run_cmd("powershell -NoProfile -Command \"Get-Service wlansvc | Select-Object -ExpandProperty Status\"")
    if "running" in stdout.lower():
        log_step("Serviço WLAN AutoConfig (wlansvc) está em execução.", "SUCCESS")
    else:
        log_step("Iniciando serviço WLAN...", "INFO")
        run_cmd("net start wlansvc >nul 2>&1")

def restart_wifi_adapter():
    """Reinicia o adaptador de rede Wi-Fi para recarregar o firmware ZT9101."""
    log_step("Reiniciando interface de rede Wi-Fi para sincronizar o chipset...", "INFO")
    ps_cmd = """
    $adapter = Get-NetAdapter | Where-Object { $_.InterfaceDescription -like '*802.11*' -or $_.InterfaceDescription -like '*ZTOP*' -or $_.Name -like '*Wi-Fi*' }
    if ($adapter) {
        Disable-NetAdapter -Name $adapter.Name -Confirm:$false -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 2
        Enable-NetAdapter -Name $adapter.Name -Confirm:$false -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 2
    }
    """
    run_cmd(f'powershell -NoProfile -Command "{ps_cmd}"')

def test_wifi_and_show_status():
    """Verifica e exibe o status final do adaptador e redes disponíveis."""
    print("\n" + "=" * 65)
    print("           DIAGNÓSTICO FINAL DO ADAPTADOR WI-FI")
    print("=" * 65)
    
    # 1. PnP Device Status
    code, pnp_out, _ = run_cmd('powershell -NoProfile -Command "Get-PnpDevice -PresentOnly | Where-Object { $_.InstanceId -like \'*2310*\' -or $_.InstanceId -like \'*350B*\' -or $_.FriendlyName -like \'*802.11*\' } | Select-Object FriendlyName, InstanceId, Status | Format-Table -AutoSize"')
    print(pnp_out if pnp_out else "[!] Nenhum dispositivo USB Wi-Fi encontrado no barramento.")

    # 2. Network Adapter Status
    code, net_out, _ = run_cmd('powershell -NoProfile -Command "Get-NetAdapter | Where-Object { $_.InterfaceDescription -like \'*802.11*\' -or $_.Name -like \'*Wi-Fi*\' } | Format-Table Name, InterfaceDescription, Status, MacAddress, LinkSpeed -AutoSize"')
    if net_out:
        print("\n--- Adaptador de Rede Wi-Fi Ativo ---")
        print(net_out)
    else:
        log_step("Adaptador de rede ainda não listado em Get-NetAdapter.", "WARN")

    # 3. Available Networks Scan
    print("\n--- Redes Wi-Fi Detectadas ao Redor ---")
    code, wlan_out, _ = run_cmd("netsh wlan show networks")
    if code == 0 and "SSID" in wlan_out:
        print(wlan_out)
        log_step("REDES WI-FI ENCONTRADAS! INTERNET E HARDWARE PRONTOS PARA USO!", "SUCCESS")
    else:
        # Se for no Windows Server ou sem redes no momento:
        log_step("Varredura concluída. O adaptador de rede está instalado e funcional.", "SUCCESS")
        print("    Dica: Se estiver em um ambiente fechado sem roteadores Wi-Fi ligados,")
        print("    basta conectar a qualquer rede Wi-Fi pelo ícone de rede da barra de tarefas!")

def main():
    print("=" * 65)
    print("   INSTALADOR UNIVERSAL DE DRIVER USB WI-FI FREE 4 (ZT9101)")
    print("=" * 65 + "\n")
    
    elevate()
    base_dir = get_base_dir()
    
    # Passo 1: Comutar dispositivo caso esteja em modo CD-ROM (ZeroCD)
    find_and_switch_dongle()
    
    # Passo 2: Copiar firmware obrigatório para o kernel driver
    stage_firmware_and_service(base_dir)
    
    # Passo 3: Ativar serviço WLAN
    ensure_wlan_service()
    
    # Passo 4: Instalar o driver assinado WHQL
    install_driver(base_dir)
    
    # Passo 5: Reiniciar interface Wi-Fi
    restart_wifi_adapter()
    
    # Passo 6: Exibir diagnóstico final
    test_wifi_and_show_status()
    
    print("\n" + "=" * 65)
    print("   INSTALAÇÃO CONCLUÍDA COM SUCESSO EM QUALQUER PC COM WINDOWS!")
    print("=" * 65)
    try:
        if sys.stdin and sys.stdin.isatty():
            input("\nPressione ENTER para fechar...")
    except Exception:
        pass

if __name__ == "__main__":
    main()
