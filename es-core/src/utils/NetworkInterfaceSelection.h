#pragma once

// Standalone network-status selection is transport-agnostic: an Internet
// connection may use Wi-Fi, wired Ethernet, USB RNDIS/ECM, a PPP modem,
// a mobile WWAN interface, or an IPv6-only link.
#include <string>
#include <vector>

namespace Utils
{
namespace Platform
{
namespace NetworkInterfaceSelection
{
struct Address
{
    std::string interfaceName;
    std::string ip;
    bool isIPv6;
};

// The default-route interface is the best local address to display, since
// Wi-Fi and USB modems can both be present at once. Prefer IPv4 for the
// legacy menu layout, but accept an IPv6-only connection.
inline std::string select(const std::vector<Address>& addresses,
                          const std::string& defaultRouteInterface)
{
    if (!defaultRouteInterface.empty())
    {
        for (int pass = 0; pass != 2; ++pass)
            for (const auto& address : addresses)
                if (address.interfaceName == defaultRouteInterface &&
                    address.isIPv6 == (pass == 1))
                    return address.ip;
    }

    for (int pass = 0; pass != 2; ++pass)
        for (const auto& address : addresses)
            if (address.isIPv6 == (pass == 1))
                return address.ip;

    return "";
}
}
}
}
