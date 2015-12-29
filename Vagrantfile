# -*- mode: ruby -*-
# vi: set ft=ruby :
hosts = {
  "rabbit-1" => "192.168.77.10",
  "rabbit-2" => "192.168.77.11",
  "rabbit-3" => "192.168.77.12"
}
Vagrant.configure("2") do |config|
  config.vm.box = "ubuntu/trusty64"
  hosts.each_with_index do |(name, ip), i|
    rmq_port = 5672 + i
    admin_port = 15672 + i
    config.vm.define name do |machine|
      machine.vm.network :private_network, ip: ip
      config.vm.hostname = "rabbit-%d" % [i + 1]
      config.vm.network :forwarded_port, guest: 5672, guest_ip: ip, host:
      rmq_port
      config.vm.network :forwarded_port, guest: 15672, guest_ip: ip, host:
      admin_port
      machine.vm.provider "virtualbox" do |v|
        v.name = name
      end
    end
  end
end
