#include "Platform.h"

#include <SDL_events.h>

#if WIN32
#include <codecvt>
#else
#include <sys/types.h>
#include <unistd.h>
#include <ifaddrs.h>
#include <net/if.h>
#include <netinet/in.h>
#include <sstream>
#include "NetworkInterfaceSelection.h"
#include <sys/stat.h>
#include <arpa/inet.h>
#include <sys/wait.h>
#include <cerrno>
#endif

#include <fcntl.h>
#include "Window.h"
#include "utils/FileSystemUtil.h"
#include "utils/StringUtil.h"
#include "Log.h"
#include "Scripting.h"
#include "Paths.h"
#include <fstream>
#include <string>
#include "renderers/Renderer.h"

// #define DEVTEST

namespace Utils
{
	namespace Platform
	{
		ProcessStartInfo::ProcessStartInfo()
		{
			window = nullptr;
			waitForExit = true;
			showWindow = true;
#ifndef WIN32
			stderrFilename = "es_launch_stderr.log";
			stdoutFilename = "es_launch_stdout.log";
#endif
		}

		ProcessStartInfo::ProcessStartInfo(const std::string& cmd)
		{
			command = cmd;
			window = nullptr;
			waitForExit = true;
			showWindow = true;
#ifndef WIN32
			stderrFilename = "es_launch_stderr.log";
			stdoutFilename = "es_launch_stdout.log";
#endif
		}

		int ProcessStartInfo::run() const
		{
			if (command.empty())
				return 1;

			if (window != nullptr)
				window->renderSplashScreen();

			std::string cmd_utf8 = command;

#ifdef WIN32
			std::wstring cmd_w = Utils::String::convertToWideString(cmd_utf8);

			DWORD dwLen = ExpandEnvironmentStringsW(cmd_w.c_str(), NULL, 0);
			if (dwLen > 0)
			{
				WCHAR* szEnvPath = new WCHAR[dwLen];

				dwLen = ExpandEnvironmentStringsW(cmd_w.c_str(), szEnvPath, dwLen);
				if (dwLen > 0)
					cmd_utf8 = Utils::String::convertFromWideString(szEnvPath);

				delete[] szEnvPath;
			}

			std::string exe;
			std::string args;
			Utils::FileSystem::splitCommand(cmd_utf8, &exe, &args);

			exe = Utils::FileSystem::getPreferredPath(exe);

			std::wstring wexe = Utils::String::convertToWideString(exe);
			std::wstring wargs = Utils::String::convertToWideString(args);

			SHELLEXECUTEINFOW lpExecInfo;
			lpExecInfo.cbSize = sizeof(SHELLEXECUTEINFOW);
			lpExecInfo.lpFile = wexe.c_str();
			lpExecInfo.fMask = SEE_MASK_DOENVSUBST | SEE_MASK_NOCLOSEPROCESS;
			lpExecInfo.hwnd = NULL;
			lpExecInfo.lpVerb = L"open"; // to open  program
			lpExecInfo.lpDirectory = NULL;
			lpExecInfo.nShow = showWindow ? SW_SHOW : SW_HIDE;  // show command prompt with normal window size
			lpExecInfo.hInstApp = (HINSTANCE)SE_ERR_DDEFAIL;   //WINSHELLAPI BOOL WINAPI result;
			lpExecInfo.lpParameters = wargs.c_str(); //  file name as an argument

			std::wstring wpath;

			// Don't set directory for relative paths
			if (!Utils::String::startsWith(exe, ".") && !Utils::String::startsWith(exe, "/") && !Utils::String::startsWith(exe, "\\"))
			{
				wpath = Utils::String::convertToWideString(Utils::FileSystem::getAbsolutePath(Utils::FileSystem::getParent(exe)));
				lpExecInfo.lpDirectory = wpath.c_str();
			}

			if (waitForExit)
				Renderer::setWindowResizable(false);

			ShellExecuteExW(&lpExecInfo);

			if (lpExecInfo.hProcess != NULL)
			{
				if (!waitForExit)
					return 0;

				if (window == nullptr)
					WaitForSingleObject(lpExecInfo.hProcess, INFINITE);
				else
				{
				

					while (WaitForSingleObject(lpExecInfo.hProcess, 50) == 0x00000102L)
					{
						bool polled = false;

						SDL_Event event;
						while (SDL_PollEvent(&event))
							polled = true;

						if (window != nullptr && polled)
							window->renderSplashScreen();
					}				
				}

				DWORD dwExitCode;
				if (!GetExitCodeProcess(lpExecInfo.hProcess, &dwExitCode))
					dwExitCode = 0;

				CloseHandle(lpExecInfo.hProcess); 
				
				if (waitForExit)
					Renderer::setWindowResizable(true);

				return dwExitCode;
			}

			if (waitForExit)
				Renderer::setWindowResizable(true);

			return 1;
#else
			// On RetroPie, terminal-driven scripts (e.g. RetroPie-Setup)
			// need their normal stdin/stdout/stderr and an unrestricted output
			// stream. The Batocera logging pipeline uses 'head -300', which
			// may break an installer that keeps writing after that limit.
			std::string cmdOutput = cmd_utf8;
#if defined(BATOCERA) || defined(RETROBAT)
			cmdOutput = "((((" + cmd_utf8 + " 2> " + Utils::FileSystem::combine(Paths::getLogPath(), stderrFilename) + " ; echo $? >&3) | head -300 > " + Utils::FileSystem::combine(Paths::getLogPath(), stdoutFilename) + ") 3>&1) | (read xs; exit $xs))";
			if (!Log::enabled())
				cmdOutput = "((((" + cmd_utf8 + " 2> /dev/null ; echo $? >&3) | head -300 > /dev/null) 3>&1) | (read xs; exit $xs))";
#endif

			if (waitForExit)
			{
				int status = system(cmdOutput.c_str());
				if (status == -1)
					return 1;

				if (WIFEXITED(status))
					return WEXITSTATUS(status);
				if (WIFSIGNALED(status))
					return 128 + WTERMSIG(status);
				return 1;
			}

			// Preserve nonblocking commands via the existing double fork.
			pid_t child = fork();
			if (child < 0)
				return 1;
			if (child == 0)
			{
				pid_t grandchild = fork();
				if (grandchild < 0)
					_exit(1);
				if (grandchild == 0)
				{
					execl("/bin/sh", "sh", "-c", cmdOutput.c_str(), (char*)NULL);
					_exit(127);
				}
				_exit(0);
			}

			int status = 0;
			while (waitpid(child, &status, 0) == -1)
			{
				if (errno != EINTR)
					return 1;
			}
			return WIFEXITED(status) ? WEXITSTATUS(status) : 1;
#endif
		}

		int runShutdownCommand()
		{
#ifdef WIN32 // windows
			return system("shutdown -s -t 0");
#elif !defined(BATOCERA) && !defined(RETROBAT)
			// Debian / RetroPie: ask systemd-logind to power down under
			// the active user's existing polkit permissions. No sudoers
			// changes and no new Bluetooth/controller services.
			return system("systemctl --no-ask-password poweroff");
#else // original Batocera / Retrobat behavior
			return system("shutdown -h now");
#endif
		}

		int runRestartCommand()
		{
#ifdef WIN32 // windows
			return system("shutdown -r -t 0");
#elif !defined(BATOCERA) && !defined(RETROBAT)
			return system("systemctl --no-ask-password reboot");
#else // original Batocera / Retrobat behavior
			return system("shutdown -r now");
#endif
		}

		static QuitMode quitMode = QuitMode::QUIT;

		int quitES(QuitMode mode)
		{
#if !defined(WIN32) && !defined(BATOCERA) && !defined(RETROBAT)
			// Fail early only when systemd is absent. The actual power request
			// MUST run after the frontend has saved metadata and released SDL.
			if (mode == QuitMode::REBOOT || mode == QuitMode::FAST_REBOOT ||
				mode == QuitMode::SHUTDOWN || mode == QuitMode::FAST_SHUTDOWN)
			{
				if (access("/usr/bin/systemctl", X_OK) != 0 &&
					access("/bin/systemctl", X_OK) != 0)
				{
					LOG(LogWarning) << "Cannot power off or reboot: systemctl not installed.";
					return 1;
				}
			}
#endif
			quitMode = mode;

			switch (quitMode)
			{
			case QuitMode::REBOOT:
			case QuitMode::FAST_REBOOT:
				Scripting::fireEvent("quit", "reboot");
				Scripting::fireEvent("reboot");
				break;

			case QuitMode::SHUTDOWN:
			case QuitMode::FAST_SHUTDOWN:
				Scripting::fireEvent("quit", "shutdown");
				Scripting::fireEvent("shutdown");
				break;
			}

			SDL_Event* quit = new SDL_Event();
			quit->type = SDL_QUIT;
			SDL_PushEvent(quit);
			return 0;
		}

		void touch(const std::string& filename)
		{
#ifndef WIN32
			int fd = open(filename.c_str(), O_CREAT | O_WRONLY, 0644);
			if (fd >= 0)
				close(fd);

			// system(("touch " + filename).c_str());
#endif
		}

		void processQuitMode()
		{

			switch (quitMode)
			{
			case QuitMode::QUIT:
				Scripting::fireEvent("quit");
				break;

			case QuitMode::RESTART:
				LOG(LogInfo) << "Restarting EmulationStation";
#if defined(WIN32) || defined(BATOCERA) || defined(RETROBAT)
				touch("/tmp/restart.please");
#endif
				break;
			case QuitMode::REBOOT:
			case QuitMode::FAST_REBOOT:
				LOG(LogInfo) << "Rebooting system";
#if defined(BATOCERA) || defined(RETROBAT) || defined(WIN32)
				touch("/tmp/reboot.please");
#endif
				if (runRestartCommand() != 0)
					LOG(LogError) << "System reboot failed. Check systemd/logind permissions.";
				break;
			case QuitMode::SHUTDOWN:
			case QuitMode::FAST_SHUTDOWN:
				LOG(LogInfo) << "Shutting system down";
#if defined(BATOCERA) || defined(RETROBAT) || defined(WIN32)
				touch("/tmp/shutdown.please");
#endif
				if (runShutdownCommand() != 0)
					LOG(LogError) << "System poweroff failed. Check systemd/logind permissions.";
				break;
			}
		}

		bool isRestartRequested()
		{
			return quitMode == QuitMode::RESTART;
		}

		bool isFastShutdown()
		{
			return quitMode == QuitMode::FAST_REBOOT || quitMode == QuitMode::FAST_SHUTDOWN;
		}

		std::string queryIPAddress()
		{
#ifdef DEVTEST
			return "127.0.0.1";
#endif

			std::string result;

#if WIN32
			// Init WinSock
			WSADATA wsa_Data;
			int wsa_ReturnCode = WSAStartup(0x101, &wsa_Data);
			if (wsa_ReturnCode != 0)
				return "";

			char* szLocalIP = nullptr;

			// Get the local hostname
			char szHostName[255];
			if (gethostname(szHostName, 255) == 0)
			{
				struct hostent* host_entry;
				host_entry = gethostbyname(szHostName);
				if (host_entry != nullptr)
					szLocalIP = inet_ntoa(*(struct in_addr*)*host_entry->h_addr_list);
			}

			WSACleanup();

			if (szLocalIP == nullptr)
				return "";

			return std::string(szLocalIP); // "127.0.0.1"
#else
			struct ifaddrs* list = nullptr;
			if (getifaddrs(&list) != 0)
				return "";

			std::vector<NetworkInterfaceSelection::Address> addresses;
			for (struct ifaddrs* it = list; it != nullptr; it = it->ifa_next)
			{
				if (!it->ifa_addr || !it->ifa_name || !(it->ifa_flags & IFF_UP) ||
					(it->ifa_flags & IFF_LOOPBACK))
					continue;

				const int family = it->ifa_addr->sa_family;
				if (family != AF_INET && family != AF_INET6)
					continue;

				char ip[INET6_ADDRSTRLEN] = {};
				const void* addr = family == AF_INET
					? static_cast<const void*>(&reinterpret_cast<const sockaddr_in*>(it->ifa_addr)->sin_addr)
					: static_cast<const void*>(&reinterpret_cast<const sockaddr_in6*>(it->ifa_addr)->sin6_addr);
				if (!inet_ntop(family, addr, ip, sizeof(ip)))
					continue;

				const std::string value(ip);
				// Neither a self-assigned IPv4 address nor an IPv6 link-local address
				// indicates a usable connection for online services.
				if (value == "0.0.0.0" || value.compare(0, 8, "169.254.") == 0 ||
					value.compare(0, 5, "fe80:") == 0 || value == "::1")
					continue;
				addresses.push_back({ it->ifa_name, value, family == AF_INET6 });
			}
			freeifaddrs(list);

			// Prefer the default-route adapter if both Wi-Fi and a USB modem
			// are connected. Interface names are *not* restricted to eth/wlan:
			// mobile PPP/WWAN, USB tethering and other Linux links all qualify.
			std::string defaultInterface;
			std::ifstream routes("/proc/net/route");
			std::string row;
			std::getline(routes, row); // header
			while (std::getline(routes, row))
			{
				std::istringstream fields(row);
				std::string iface, destination;
				if (fields >> iface >> destination && destination == "00000000")
				{
					defaultInterface = iface;
					break;
				}
			}
			result = NetworkInterfaceSelection::select(addresses, defaultInterface);
#endif

			return result;

		}

		BatteryInformation queryBatteryInformation()
		{
			BatteryInformation ret;
			ret.hasBattery = false;
			ret.isCharging = false;
			ret.level = 0;

#ifdef DEVTEST
			ret.hasBattery = true;
			ret.isCharging = true;
			ret.level = 33;

			time_t     clockNow = time(0);
			struct tm  clockTstruct = *localtime(&clockNow);
			ret.level = clockTstruct.tm_min;

			return ret;
#endif

#ifdef WIN32
			SYSTEM_POWER_STATUS systemPowerStatus;
			if (GetSystemPowerStatus(&systemPowerStatus))
			{
				if ((systemPowerStatus.BatteryFlag & 128) == 128)
					ret.hasBattery = false;
				else
				{
					ret.hasBattery = true;
					ret.isCharging = (systemPowerStatus.BatteryFlag & 8) == 8;
					ret.level = systemPowerStatus.BatteryLifePercent;
				}
			}
			else
				ret.hasBattery = false;

			return ret;

#endif

			static std::string batteryStatusPath;
			static std::string batteryCapacityPath;
			static std::string batteryCurrChargePath;
			static std::string batteryMaxChargePath;
			static std::string batteryCurrentPath;

			// Find battery path - only at the first call
			if (batteryStatusPath.empty())
			{
				std::string batteryRootPath;
				std::string fuelgaugeRootPath;
				std::string chargerRootPath;

				auto files = Utils::FileSystem::getDirContent("/sys/class/power_supply");
				for (auto file : files)
				{
					if ((Utils::String::toLower(file).find("/bat") != std::string::npos) && (batteryRootPath.empty()))
						batteryRootPath = file;

					// Qualcomm devices use "qcom-battery"
					if ((Utils::String::toLower(file).find("/qcom-battery") != std::string::npos) && (batteryRootPath.empty()))
						batteryRootPath = file;

					if ((Utils::String::toLower(file).find("fuel") != std::string::npos) && (fuelgaugeRootPath.empty()))
						fuelgaugeRootPath = file;

					if ((Utils::String::toLower(file).find("charger") != std::string::npos) && (chargerRootPath.empty()))
						chargerRootPath = file;
				}

				// If there's no battery device, look for discrete charger and fuel gauge
				if (batteryRootPath.empty())
				{
					if (!fuelgaugeRootPath.empty())
					{
						batteryCurrChargePath = fuelgaugeRootPath + "/charge_now";
						batteryMaxChargePath = fuelgaugeRootPath + "/charge_full";
						batteryCapacityPath = ".";
						batteryCurrentPath = ".";
						// If there's a fuel gauge without "charge_now" or "charge_full" property, don't poll it
						if ((!Utils::FileSystem::exists(batteryCurrChargePath)) || (!Utils::FileSystem::exists(batteryMaxChargePath)))
						{
							batteryCurrChargePath = ".";
							batteryMaxChargePath = ".";
						}
					}
					if (!chargerRootPath.empty())
						batteryStatusPath = chargerRootPath + "/status";
					else
						batteryStatusPath = ".";
				}
				else
				{
					batteryStatusPath = batteryRootPath + "/status";
					batteryCapacityPath = batteryRootPath + "/capacity";
					batteryCurrentPath = batteryRootPath + "/current_avg";
				}
			}

			if ((batteryStatusPath.length() <= 1) && (batteryCurrChargePath.length() <= 1))
			{
				ret.hasBattery = false;
				ret.isCharging = false;
				ret.level = 0;
			}
			else
			{
				ret.hasBattery = true;
				std::string chargerStatus;
				chargerStatus = Utils::String::replace(Utils::FileSystem::readAllText(batteryStatusPath), "\n", "");
				ret.isCharging = ((chargerStatus != "Not charging") && (chargerStatus != "Discharging"));

				if (batteryCurrentPath.length() > 1 && Utils::FileSystem::exists(batteryCurrentPath))
				{
					int currentVal = Utils::String::toInteger(Utils::FileSystem::readAllText(batteryCurrentPath));
					if (currentVal > 0)
						ret.isCharging = true;
				}

				// If reading from fuel gauge, we have to calculate remaining charge
				if (batteryCapacityPath.length() <= 1)
				{
					if ((!batteryCurrChargePath.empty()) && (!batteryMaxChargePath.empty()))
					{
						float now = std::stof(Utils::FileSystem::readAllText(batteryCurrChargePath).c_str());
						float full = std::stof(Utils::FileSystem::readAllText(batteryMaxChargePath).c_str());
						ret.level = int(round((now / full) * 100));
					}
				}
				else
				{
					std::ifstream file(batteryCapacityPath);
					if (file.is_open())
					{
						std::string buffer;
						std::getline(file, buffer);
						file.close();
						if (!buffer.empty())
						{
							ret.level = Utils::String::toInteger(buffer);
						}
						else
						{
							LOG(LogError) << "Error reading: " << batteryCapacityPath;
						}
					}
					else
					{
						LOG(LogError) << "Error opening: " << batteryCapacityPath;
					}
				}
			}

			return ret;
		}

#if WIN32
		static bool _getWindowsVersion(WORD& major, WORD& minor, WORD& build, WORD& revision)
		{
			// Use product version in kernel32.dll to have real Windows version as we don't have a compatibility manifest (GetVersion is limited to 6.2)
			HMODULE kernel32Module = GetModuleHandle("kernel32.dll");
			if (kernel32Module != nullptr)
			{
				wchar_t filePath[MAX_PATH];
				DWORD length = GetModuleFileNameW(kernel32Module, filePath, MAX_PATH);
				if (length > 0)
				{
					DWORD dummy;
					DWORD versionSize = GetFileVersionInfoSizeW(filePath, &dummy);

					std::vector<char> versionData(versionSize);
					if (GetFileVersionInfoW(filePath, 0, versionSize, versionData.data()))
					{
						VS_FIXEDFILEINFO* fileInfo;
						UINT fileInfoSize;

						if (VerQueryValueW(versionData.data(), L"\\", reinterpret_cast<void**>(&fileInfo), &fileInfoSize))
						{
						    major = HIWORD(fileInfo->dwProductVersionMS);
							minor = LOWORD(fileInfo->dwProductVersionMS);
							build = HIWORD(fileInfo->dwProductVersionLS);
							revision = LOWORD(fileInfo->dwProductVersionLS);

							return true;
						}
					}
				}
			}

			return false;
		}

		bool isWindows11()
		{
			WORD major, minor, build, revision;
			if (_getWindowsVersion(major, minor, build, revision))
				return major > 10 || (major == 10 && (minor > 0 || build >= 22000));

			return false;
		}
#endif

		std::string getArchString()
		{
#if WIN32
			return "windows";
#else
			std::string arch = Utils::FileSystem::readAllText("/usr/share/batocera/batocera.arch");
			if (!arch.empty())
				return arch;

#if X86
			return "x86";
#endif

#if X86_64
			return "x86_64";
#endif

#if RPIZERO2
			return "rpizero2";
#endif

#if RPI1 || BCM2835
			return "rpi1";
#endif

#if RPI2
			return "rpi2";
#endif

#if RPI3 || BCM2836 || BCM2837
			return "rpi3";
#endif

#if RPI4 || BCM2711
			return "rpi4";
#endif

#if ODROIDXU4
			return "odroidxu4";
#endif

#if RK3128
			return "rk3128";
#endif

#if RK3288
			return "rk3288";
#endif

#if RK3326
			return "rk3326";
#endif

#if RK3328
			return "rk3328";
#endif

#if RK3399
			return "rk3399";
#endif

#if RK3568
			return "rk3568";
#endif

#if RK3588
			return "rk3588";
#endif

#if H3
			return "h3";
#endif

#if H5
			return "h5";
#endif

#if H6
			return "h6";
#endif

#if H616
			return "h616";
#endif

#if S812
			return "s812";
#endif

#if S905
			return "s905";
#endif

#if S912
			return "s912";
#endif

#if S905GEN2
			return "s905gen2";
#endif

#if S905GEN3
			return "s905gen3";
#endif

#if S922X
			return "s922x";
#endif

#endif

			return "";
		}
	}
}
