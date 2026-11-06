#pragma once

#include "GuiComponent.h"
#include "components/MenuComponent.h"
#include "components/BusyComponent.h"

#include <thread>
#include <memory>
#include <atomic>

class GuiBluetoothPair : public MenuComponent
{
public:
	GuiBluetoothPair(Window* window);
	~GuiBluetoothPair();

	virtual bool input(InputConfig* config, Input input) override;
	virtual std::vector<HelpPrompt> getHelpPrompts() override;
	virtual void updateSize() override;

	virtual void render(const Transform4x4f &parentTrans) override;
	virtual void update(int deltaTime) override;

private:
	std::thread* mThread;
	std::shared_ptr<std::atomic<bool>> mAlive;
	void		 loadDevicesAsync();

	void		 onPairDevice(const std::string& macAddress);

	std::function<void(std::string)> mSaveFunction;

	BusyComponent mBusyAnim;

	bool mIsPairing;

	static GuiBluetoothPair*	Instance;
};
