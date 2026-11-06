#pragma once
#include "guis/GuiSettings.h"
#include "LocaleES.h"
#include "Window.h"
#include "guis/GuiMsgBox.h"
#include "components/OptionListComponent.h"
#include "RetroPieAchievementConfig.h"

// Standalone settings deliberately do not invoke the legacy account/API login.
class GuiRetroPieAchievementsSettings : public GuiSettings
{
public:
    explicit GuiRetroPieAchievementsSettings(Window* window)
        : GuiSettings(window, _("RETROACHIEVEMENT SETTINGS"), _("SAVE"),
            [](GuiSettings* gui) { static_cast<GuiRetroPieAchievementsSettings*>(gui)->commit(); })
        , mSnapshot(RetroPieAchievementConfig::read(configPath()))
    {
        setSave(false); // Back/start/cancel must never write settings.
        if (!mSnapshot.valid) {
            addEntry(_("RETROARCH CONFIGURATION COULD NOT BE READ"));
            return;
        }
        addGroup(_("RETROARCH GLOBAL SETTINGS"));
        addWithDescription(_("USERNAME"), mSnapshot.username.empty() ? _("NOT CONFIGURED") : mSnapshot.username, nullptr);
        addEntry(_("MANAGE YOUR ACCOUNT IN RETROARCH"));
        addEntry(_("SYSTEM, CORE AND GAME OVERRIDES MAY TAKE PRECEDENCE"));
        const std::vector<std::pair<std::string, std::string>> rows = {
            {"cheevos_enable", "RETROACHIEVEMENTS"},
            {"cheevos_hardcore_mode_enable", "HARDCORE MODE"},
            {"cheevos_leaderboards_enable", "LEADERBOARDS"},
            {"cheevos_verbose_enable", "VERBOSE MODE"},
            {"cheevos_richpresence_enable", "RICH PRESENCE"},
            {"cheevos_start_active", "ENCORE MODE"},
            {"cheevos_auto_screenshot", "AUTOMATIC SCREENSHOT"},
            {"cheevos_challenge_indicators", "CHALLENGE INDICATORS"},
            {"cheevos_test_unofficial", "UNOFFICIAL ACHIEVEMENTS"},
            {"cheevos_unlock_sound_enable", "UNLOCK SOUND"}
        };
        for (const auto& row : rows) {
            auto option = std::make_shared<OptionListComponent<std::string>>(window, _(row.second.c_str()), false);
            const auto selected = mSnapshot.option(row.first);
            option->add(_("DEFAULT"), "", selected.empty());
            option->add(_("ON"), "true", selected == "true");
            option->add(_("OFF"), "false", selected == "false");
            addWithLabel(_(row.second.c_str()), option);
            mOptions[row.first] = option;
        }
    }
private:
    static std::string configPath() { return "/opt/retropie/configs/all/retroarch.cfg"; }
    RetroPieAchievementConfig::Snapshot mSnapshot;
    std::map<std::string, std::shared_ptr<OptionListComponent<std::string>>> mOptions;

    void commit() {
        std::map<std::string, std::string> requested;
        for (const auto& item : mOptions) requested[item.first] = item.second->getSelected();
        const auto error = RetroPieAchievementConfig::save(configPath(), mSnapshot, requested);
        if (!error.empty()) {
            mWindow->pushGui(new GuiMsgBox(mWindow, _(error.c_str())));
            return;
        }
        Window* window = mWindow;
        close();
        window->pushGui(new GuiMsgBox(window, _("RETROARCH ACHIEVEMENT SETTINGS SAVED. RELOAD THE GAME LIST TO UPDATE THEME ICONS.")));
    }
};
