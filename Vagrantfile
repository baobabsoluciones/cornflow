VAGRANTFILE_API_VERSION = "2"
$bootstrap=<<SCRIPT
sudo apt-get update
sudo apt-get install \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg-agent \
    software-properties-common -y
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
sudo apt-key fingerprint 0EBFCD88
sudo add-apt-repository \
   "deb [arch=amd64] https://download.docker.com/linux/ubuntu \
   $(lsb_release -cs) \
   stable"
sudo apt-get update
sudo apt-get install docker-ce docker-ce-cli containerd.io -y
sudo usermod -aG docker vagrant
sudo systemctl enable docker
sudo systemctl restart docker
sudo apt install docker-compose -y
cd /vagrant && docker-compose up -d --build 
SCRIPT

Vagrant.configure(VAGRANTFILE_API_VERSION) do |config|
config.vm.box = "ubuntu/bionic64"
config.vm.network "private_network", ip: "192.168.33.10"
config.vm.provider "virtualbox" do |vb|
vb.customize ["modifyvm", :id, "--memory", "2048"]
end
config.vm.provision :shell, inline: $bootstrap
end
