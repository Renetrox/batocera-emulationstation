#include "../es-core/src/utils/NetworkInterfaceSelection.h"
#include <cassert>
#include <string>
#include <vector>

int main()
{
    using namespace Utils::Platform::NetworkInterfaceSelection;
    std::vector<Address> addresses = {
        {"wlan0", "192.168.1.35", false},
        {"ppp0", "10.54.31.9", false},
        {"wwan0", "192.0.2.45", false},
        {"enx28f8", "172.16.42.1", false},
        {"wwan0", "2001:db8::1", true}
    };
    assert(select(addresses, "ppp0") == "10.54.31.9");
    assert(select(addresses, "wwan0") == "192.0.2.45");
    assert(select(addresses, "enx28f8") == "172.16.42.1");
    assert(select(addresses, "wlan0") == "192.168.1.35");
    assert(select(addresses, "") == "192.168.1.35");
    assert(select({{"ppp0", "2001:db8::2", true}}, "ppp0") == "2001:db8::2");
    assert(select({}, "ppp0").empty());
}
