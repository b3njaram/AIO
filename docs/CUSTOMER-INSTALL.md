# Guided JobbiSoft Home installation (pilot)
 
## Standard host
 
Ubuntu Server 24.04 LTS x86-64, no desktop, one dedicated customer-owned machine or VM. Use a local SSD for Linux/Docker databases; size RAM and media storage to workload. Start with 16 GB RAM (32 GB for larger workloads); test actual capacity, thermals and transcoding. No unattended OS disk formatting is supported. Use the official Ubuntu installer, explicit approved disk selection, customer-local operator account and optional OpenSSH.
 
## One command after OS setup
 
Mount the reviewed data and independent backup filesystems first. Verify persistence in /etc/fstab, physical disk identities, ownership and capacity; do not reuse a personal server's data directory. On the dedicated host, install Git if necessary:
 
    sudo apt update
    sudo apt install git python3
    git clone https://github.com/b3njaram/AIO.git ~/jobbi-aio
    cd ~/jobbi-aio
 
Check out a reviewed release commit rather than arbitrary main or an unvalidated branch. For pilot testing only use the reviewed candidate SHA.
 
    python3 scripts/setup-customer.py --name home --data-root /srv/jobbi-data --backup-root /mnt/jobbi-backup
 
Review the command plan, then repeat with --apply. The setup installs Docker packages if absent, checks capacity and Docker access, creates the instance, starts selected apps, waits for HTTP reachability and prints onboarding instructions. If Docker access is missing, grant it intentionally only to the trusted local operator (Docker group is root-equivalent), log out/in and rerun before any instance was created. Existing Docker configuration is retained. Core apps default to all except Pi-hole. Optional --quote /path/to/jobbi-home-config.json selects the customer apps; --apps explicitly overrides it. Prices, mirroring and disk capacity are never treated as hardware validation. The script refuses existing instances and does not erase data. If stopped after instance preparation, inspect the progress and frozen deployment rather than deleting or rerunning blindly.
 
Docker restart policies bring services back when the enabled daemon starts. Test a real reboot and mount availability. There is no desktop login requirement. Separate OS/volume failure and backup recovery are still physical acceptance tests.
 
## Customer participation
 
Complete docs/HANDOFF.md for application accounts and sample-data tests. Use trusted SSH forwarding for initial setup, then a customer-owned Tailscale account and private HTTPS per docs/PRIVATE-ACCESS.md. No personal tailnet credentials, public Funnel, public router ports or automatic DNS changes. Use the maintenance guide for independent encrypted backup, restore and supervised upgrades. Never mark a service accepted solely because HTTP responds.
 
## Future installer
 
A USB-based Ubuntu autoinstall workflow can automate packages, the operator setup and first-boot provisioning, but must identify and explicitly confirm the intended OS disk before erasing it. Keep account enrollment and recovery secrets customer-controlled. An unattended ISO and real-machine first-boot/reboot verification are not implemented or certified yet.
