# Adaptador USB Wi-Fi "Free 4" (ZT9101 / 9101DV20) - Instalador Universal

[![Platform](https://img.shields.io/badge/Platform-Windows%207%20%7C%208%20%7C%2010%20%7C%2011%20%7C%20Server-blue.svg)](https://microsoft.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Driver: WHQL](https://img.shields.io/badge/Driver-Microsoft%20WHQL%20Signed-success.svg)](#)

Solução autônoma e instalador universal para adaptadores USB Wi-Fi 802.11n genéricos baseados no chipset **ZTOPMICRO ZT9101 / 9101DV20** (comercializados como *"WiFi Free 4"*, *"Driver Free 802.11n"*, *"Mini Wi-Fi Dongle"*).

---

## 🔍 O Problema Comum deste Adaptador

Muitos usuários compram adaptadores Wi-Fi USB genéricos marcados com **"WiFi Free 4"** e enfrentam dois problemas críticos ao conectar no Windows:

1. **Tecnologia ZeroCD (Modo Duplo de Fábrica)**:
   * Ao ser inserido na porta USB, o hardware **não** se apresenta de imediato como placa de rede. Ele inicia como uma unidade de CD-ROM / Armazenamento Virtual (`USB\VID_2310&PID_1A2B`).
   * Para virar um adaptador Wi-Fi (`USB\VID_2310&PID_9086` ou `USB\VID_350B&PID_9101`), o sistema precisa emitir um comando de ejeção SCSI (`IOCTL_STORAGE_EJECT_MEDIA`). Sem isso, o Windows continua enxergando apenas um CD-ROM virtual.

2. **Exigência de Microcódigo Externo (`firmware.bin`)**:
   * O driver de kernel (`usbwifi_ndis6.sys`) exige obrigatoriamente a presença do arquivo `firmware.bin` no caminho fixo:
     * `C:\Program Files (x86)\ZTOPMICRO\firmware.bin` (em Windows 64-bit)
     * `C:\Program Files\ZTOPMICRO\firmware.bin` (em Windows 32-bit)
   * Se o usuário instalar apenas o arquivo `.inf` pelo Gerenciador de Dispositivos, o Windows falhará ao iniciar o dispositivo com **Erro Código 10** ou **Erro Código 43** (*usb firmware open failed*).

3. **Incompatibilidade em Windows Server**:
   * Em edições Windows Server, a funcionalidade de rede sem fio (`Wireless-Networking` / `wlansvc` / `vwifibus.sys`) vem desativada por padrão, impedindo que o driver NDIS complete a instalação sem o Virtual WiFi Bus.

---

## 🚀 Como Esta Solução Resolve Tudo Automaticamente

O script `wifi_installer.py` (e o executável compilado):
1. **Comuta a Porta USB**: Detecta a unidade virtual `ZTOPMICRO` e ejeta a partição automaticamente, fazendo o chip USB renascer instantaneamente como placa Wi-Fi.
2. **Implanta o Firmware**: Cria os diretórios necessários em `Program Files` e copia o `firmware.bin`.
3. **Instala o Serviço Auto_eject**: Configura um serviço leve no Windows para que, ao desplugar e plugar o adaptador em qualquer porta, a comutação para Wi-Fi ocorra em menos de 1 segundo.
4. **Instala Drivers Oficiais WHQL**: Detecta a arquitetura (64-bit ou 32-bit) e instala via `pnputil` os drivers certificados pela Microsoft (**Microsoft Windows Hardware Compatibility Publisher**), garantindo compatibilidade sem avisos de assinatura no Windows 11, 10, 8 e 7.
5. **Configura o WLAN AutoConfig (`wlansvc`)**: Garante que o serviço de redes sem fio do Windows esteja ativo e inicializado automaticamente.

---

## 📁 Estrutura do Repositório

```text
├── wifi_installer.py          # Script principal em Python
├── Instalar_WiFi.bat          # Lançador em lote (.bat) com auto-elevação
├── LEIA-ME_INSTRUCOES.txt     # Guia rápido de uso
├── payload/
│   ├── drivers/
│   │   ├── x64/               # Drivers NDIS6 64-bit assinados WHQL (.inf, .sys, .cat)
│   │   ├── x86/               # Drivers NDIS6 32-bit assinados WHQL (.inf, .sys, .cat)
│   │   └── xp/                # Drivers legados NDIS5 para Windows XP
│   └── service/
│       ├── Auto_eject.exe     # Utilitário de monitoramento de porta USB
│       ├── firmware.bin       # Microcódigo binário do chip ZT9101
│       └── uninstall.exe      # Desinstalador
└── README.md
```

---

## 💻 Instruções de Uso

### Opção 1: Executável Direto (1 Clique)
1. Conecte o USB Wi-Fi no computador.
2. Baixe o pacote e dê dois cliques no arquivo `Instalador_WiFi_Free4.exe` (ou execute `Instalar_WiFi.bat`).
3. Confirme a permissão de Administrador quando solicitado pelo Windows.
4. O programa executará o diagnóstico e a rede Wi-Fi estará pronta para uso em segundos.

### Opção 2: Via Python
```powershell
python wifi_installer.py
```

---

## 🛡️ Licença
Distribuído sob a licença MIT. Consulte [LICENSE](LICENSE) para mais informações.
