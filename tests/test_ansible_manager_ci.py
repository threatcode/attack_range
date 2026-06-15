from attack_range.managers.ansible_manager import AnsibleManager


def test_strip_dns_from_wireguard_config_content():
    content = """[Interface]
Address = 10.0.1.11/32
PrivateKey = abc
DNS = 1.1.1.1, 8.8.8.8

[Peer]
PublicKey = xyz
AllowedIPs = 10.0.1.0/24, 10.0.2.0/24
Endpoint = 1.2.3.4:51820
"""
    stripped = AnsibleManager._strip_dns_from_wireguard_config_content(content)
    assert "DNS" not in stripped
    assert "Address = 10.0.1.11/32" in stripped
    assert "AllowedIPs = 10.0.1.0/24, 10.0.2.0/24" in stripped
