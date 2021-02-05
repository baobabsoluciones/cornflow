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
docker-compose -f /vagrant/docker-compose-cornflow-celery.yml up --scale worker=2 -d 
SCRIPT

Vagrant.configure(VAGRANTFILE_API_VERSION) do |config|
config.vm.box = "bento/ubuntu-20.04"
config.vm.network "private_network", ip: "192.168.33.10"
config.vm.provider "virtualbox" do |vb|
config.vm.network "forwarded_port", guest: 5000, host: 5000
config.vm.network "forwarded_port", guest: 8080, host: 8080
config.vm.network "forwarded_port", guest: 5555, host: 5555
vb.customize ["modifyvm", :id, "--memory", "2048"]
end
config.vm.provision :shell, inline: $bootstrap
end
