-- ============================================================
--   BADAN METEOROLOGI, KLIMATOLOGI & GACHA (BMKG THE PORTAL)
--   V2 INTERACTIVE WEATHER APP DASHBOARD & DUAL-WATCHDOG
-- ============================================================

local g = getgenv and getgenv() or _G

-- 1. SINGLETON KILLER (PREVENTS DUPLICATES ACROSS TELEPORTS)
g.BMKG_STOP = true
if g.BMKG_CLEANUP then
    pcall(g.BMKG_CLEANUP)
    task.wait(0.3)
end

local INSTANCE_ID = tick()
g.BMKG_INSTANCE_ID = INSTANCE_ID
g.BMKG_STOP = false
local activeConnections = {}

g.BMKG_CLEANUP = function()
    g.BMKG_INSTANCE_ID = nil
    g.BMKG_STOP = true
    for _, conn in ipairs(activeConnections) do
        pcall(function() conn:Disconnect() end)
    end
    activeConnections = {}
    print("[BMKG] Previous script instance safely terminated.")
end

local function isCurrentInstance()
    return (not g.BMKG_STOP) and (g.BMKG_INSTANCE_ID == INSTANCE_ID)
end

local HttpService = game:GetService("HttpService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Players = game:GetService("Players")
local VirtualUser = game:GetService("VirtualUser")
local Workspace = game:GetService("Workspace")
local StarterGui = game:GetService("StarterGui")
local GuiService = game:GetService("GuiService")
local CoreGui = game:GetService("CoreGui")
local LocalPlayer = Players.LocalPlayer

-- Configuration & Webhooks
local DISCORD_WEBHOOK = "https://discord.com/api/webhooks/1540322408672534558/4UCzxOUqPmWeE-GYbWZ0ebZmyFB0ewE4dTZZziInsfZwnOzVJ9A4wXNO0dIdUfJzX7fC"
local CLOUD_API_URL   = "https://the-portal-bmkg.onrender.com" -- Set your Render / Cloud service URL here (leave "" to send embeds directly to Discord)
local ECLIPSE_ROLE_ID = "1557371112357367849"
local OWNER_USER_ID   = "1050406766858481725" -- Alert ping when offline
local STATE_FILE_NAME = "bmkg_last_state.json"
local AUTORUN_FILE    = "bmkg_autorun.lua"
local lastCloudPing   = 0
local lastCardWeather = nil
local lastCardUrl     = nil

-- Weather-Specific Role Mappings (Newly Created POTATO Server Roles)
local WEATHER_ROLES = {
    ["NorthernLights"]= "1557371108032913521", -- Northern Lights (Aurora & Upgrade)
    ["Nightmare"]     = "1557371110193106954", -- Nightmare (Blood Moon & EXP)
    ["PortalEclipse"] = "1557371112357367849", -- Portal Eclipse (Rift & Boss)
    ["Snow"]          = "1557371115024941056", -- Snow (+20% Shop Surcharge)
    ["HeavyRain"]     = "1557371120422883411", -- Heavy Rain (+10% Shop Surcharge)
    ["Gale"]          = "1557371122318708857", -- Gale (+10% Shop Surcharge)
    ["NormalRain"]    = "1557371124222787594", -- Rain (+5% Shop & Auto-Water)
    ["Rain"]          = "1557371124222787594", -- Rain (+5% Shop & Auto-Water)
    ["Drizzle"]       = "1557371125971820554", -- Drizzle (+5% Shop & Auto-Water)
    ["Windy"]         = "1557371127326572579", -- Windy (+5% Shop & Wind Modifiers)
    ["Dry"]           = "1557371128920547460"  -- Dry (Sunny & Normal Prices)
}
local ECLIPSE_ROLE_ID = "1557371112357367849"

local SLOT_ROLL_HOURS = {
    [1] = "4:00 AM",
    [2] = "8:00 AM",
    [3] = "12:00 PM",
    [4] = "4:00 PM",
    [5] = "8:00 PM",
    [6] = "12:00 AM"
}

-- Safe Teleport Bridge
local queueTeleport = queue_on_teleport or (syn and syn.queue_on_teleport) or (fluxus and fluxus.queue_on_teleport)
if queueTeleport then
    local teleConn = LocalPlayer.OnTeleport:Connect(function(state)
        if state == Enum.TeleportState.InProgress then
            pcall(function()
                queueTeleport([[
                    task.spawn(function()
                        repeat task.wait(0.5) until game:IsLoaded() and game:GetService("Players").LocalPlayer
                        task.wait(2)
                        if isfile and readfile and isfile("bmkg_autorun.lua") then
                            local src = readfile("bmkg_autorun.lua")
                            if src and #src > 50 then
                                local fn = loadstring(src)
                                if fn then fn() end
                            end
                        end
                    end)
                ]])
            end)
        end
    end)
    table.insert(activeConnections, teleConn)
end

-- ============================================================
-- 2. OFFLINE & DISCONNECT SENSOR
-- ============================================================

local hasSentOfflineAlert = false

local function sendOfflineEmergencyAlert(reason)
    if hasSentOfflineAlert then return end
    hasSentOfflineAlert = true

    local shortJobId = string.sub(game.JobId ~= "" and game.JobId or "Online", 1, 8)
    local payload = {
        content = string.format("🚨 <@%s> **PERINGATAN: RADAR TERPUTUS / ROBLOX OFFLINE!**", OWNER_USER_ID),
        allowed_mentions = {
            users = { OWNER_USER_ID }
        },
        embeds = {{
            title = "🔴 BMKG Observatory Offline Alert",
            description = string.format("⚠️ **Status**: Bot radar kehilangan koneksi dengan server!\n\n> 📋 **Penyebab / Reason:** `%s`\n> 🌐 **Server JobId:** `%s`\n> ⏰ **Waktu / Time:** <t:%d:F> (<t:%d:R>)\n\n*Segera periksa Roblox Client untuk menyambungkan kembali radar!*", reason or "Disconnected from game server", shortJobId, os.time(), os.time()),
            color = 0xE74C3C,
            footer = { text = "Badan Meteorologi Klimatologi dan Gacha (BMKG) • Emergency System" },
            timestamp = DateTime.now():ToIsoDate()
        }}
    }

    local httpRequest = (syn and syn.request) or (http and http.request) or http_request or request
    if httpRequest then
        pcall(function()
            httpRequest({
                Url = DISCORD_WEBHOOK,
                Method = "POST",
                Headers = { ["Content-Type"] = "application/json" },
                Body = HttpService:JSONEncode(payload)
            })
        end)
    end
end

local errConn = GuiService.ErrorMessageChanged:Connect(function(msg)
    if msg and #msg > 0 and not hasSentOfflineAlert then
        sendOfflineEmergencyAlert("Roblox Disconnect: " .. tostring(msg))
    end
end)
table.insert(activeConnections, errConn)

pcall(function()
    local promptGui = CoreGui:FindFirstChild("RobloxPromptGui")
    if promptGui then
        local promptContainer = promptGui:FindFirstChild("promptOverlay")
        if promptContainer then
            local promptConn = promptContainer.ChildAdded:Connect(function(child)
                if not hasSentOfflineAlert and child.Name == "ErrorPrompt" then
                    task.wait(0.2)
                    local errorTitle = child:FindFirstChild("TitleFrame") and child.TitleFrame:FindFirstChild("ErrorTitle")
                    local errorMsg = child:FindFirstChild("MessageArea") and child.MessageArea:FindFirstChild("ErrorMsg")
                    local reasonText = (errorTitle and errorTitle.Text or "Disconnected") .. " - " .. (errorMsg and errorMsg.Text or "")
                    sendOfflineEmergencyAlert(reasonText)
                end
            end)
            table.insert(activeConnections, promptConn)
        end
    end
end)

pcall(function()
    game:BindToClose(function()
        if not hasSentOfflineAlert then
            sendOfflineEmergencyAlert("Roblox Client Closed / Terminated")
            task.wait(1)
        end
    end)
end)

-- Core Game Modules
local Core = ReplicatedStorage:WaitForChild("Shared", 15):WaitForChild("Core", 15)
local Constants = require(Core:WaitForChild("Constants", 15))

local Client = LocalPlayer:WaitForChild("PlayerScripts", 15):WaitForChild("Client", 15)
local NetworkController = require(Client:WaitForChild("Network", 15):WaitForChild("NetworkController", 15))

local WeatherController = nil
pcall(function()
    WeatherController = require(Client:WaitForChild("World", 10):WaitForChild("WeatherController", 10))
end)

local Schedule = Constants.WeeklyBoss.Schedule
local DisplayNames = Constants.Weather.DisplayNames or {}
local Probabilities = Constants.Weather.SeasonalProbabilities or {}
local EffectsTable = Constants.Weather.Effects or {}
local FogSettings = Constants.Weather.FogSettings or {}

local TIMEZONE_OFFSET = 7 * 3600 -- GMT+7
local TOTAL_YEAR_CYCLE_SECONDS = 691200 -- 8 Real Days
local WEATHER_SLOT_SECONDS = 7200 -- 2 Real Hours per weather slot

-- ============================================================
-- 3. STATE PERSISTENCE & GAP DETECTION ENGINE
-- ============================================================

local function loadSavedState()
    if isfile and readfile and isfile(STATE_FILE_NAME) then
        local success, content = pcall(readfile, STATE_FILE_NAME)
        if success and content and #content > 5 then
            local successDecode, data = pcall(HttpService.JSONDecode, HttpService, content)
            if successDecode and type(data) == "table" then
                return data
            end
        end
    end
    return nil
end

local function saveState(data)
    if writefile and data then
        local success, json = pcall(HttpService.JSONEncode, HttpService, data)
        if success and json then
            pcall(writefile, STATE_FILE_NAME, json)
        end
    end
end

-- ============================================================
-- 4. BULLETPROOF 24/7 ANTI-AFK ENGINE
-- ============================================================

if getconnections then
    pcall(function()
        for _, conn in pairs(getconnections(LocalPlayer.Idled)) do
            if conn.Disable then
                conn:Disable()
            elseif conn.Disconnect then
                conn:Disconnect()
            end
        end
    end)
end

local afkConn = LocalPlayer.Idled:Connect(function()
    if not isCurrentInstance() then return end
    pcall(function()
        VirtualUser:CaptureController()
        VirtualUser:ClickButton2(Vector2.new(0, 0))
        VirtualUser:Button2Down(Vector2.new(0, 0), Workspace.CurrentCamera.CFrame)
        task.wait(0.2)
        VirtualUser:Button2Up(Vector2.new(0, 0), Workspace.CurrentCamera.CFrame)
    end)
end)
table.insert(activeConnections, afkConn)

task.spawn(function()
    while isCurrentInstance() do
        task.wait(240)
        if not isCurrentInstance() then break end
        pcall(function()
            VirtualUser:CaptureController()
            VirtualUser:ClickButton2(Vector2.new(0, 0))
        end)
    end
end)

-- ============================================================
-- 5. WEATHER APP METEOROLOGY & GRAPHIC TELEMETRY HELPERS
-- ============================================================

local SEASONS_DATA = {
    ["Spring"] = { next = "Summer", endPos = 0.25, icon = "🌱", nextIcon = "☀️" },
    ["Summer"] = { next = "Autumn", endPos = 0.50, icon = "☀️", nextIcon = "🍂" },
    ["Autumn"] = { next = "Winter", endPos = 0.75, icon = "🍂", nextIcon = "❄️" },
    ["Winter"] = { next = "Spring", endPos = 1.00, icon = "❄️", nextIcon = "🌱" }
}

local WEATHER_ICONS = {
    ["PortalEclipse"] = "🌑",
    ["Nightmare"]     = "👁️",
    ["NorthernLights"]= "🌌",
    ["HeavyRain"]     = "🌧️",
    ["NormalRain"]    = "🌦️",
    ["Rain"]          = "🌦️",
    ["Drizzle"]       = "🌦️",
    ["Snow"]          = "❄️",
    ["Windy"]         = "💨",
    ["Gale"]          = "🌪️",
    ["Dry"]           = "☀️"
}

local WEATHER_COLORS = {
    ["PortalEclipse"] = 0x8E44AD, -- Cosmic Purple
    ["Nightmare"]     = 0x8B0000, -- Blood Crimson
    ["NorthernLights"]= 0x00F0A8, -- Aurora Emerald
    ["HeavyRain"]     = 0x2980B9, -- Dark Storm Blue
    ["NormalRain"]    = 0x3498DB, -- Sky Rain Blue
    ["Rain"]          = 0x3498DB,
    ["Drizzle"]       = 0x5DADE2, -- Light Cyan Drizzle
    ["Snow"]          = 0x00D2D3, -- Blizzard Frost
    ["Windy"]         = 0x1ABC9C, -- Breeze Teal
    ["Gale"]          = 0x16A085, -- Storm Emerald
    ["Dry"]           = 0xF39C12  -- Solar Amber
}

local BMKG_QUOTES = {
    ["NorthernLights"]= "🌌 **INFO BMKG / ADVISORY**: Fenomena Aurora (Northern Lights)! Langit bercahaya hijau magis, berkah EXP & buff melimpah!\n> *(Northern Lights active! Ethereal auroral skies, blessed buffs & increased luck)*",
    ["Nightmare"]     = "👁️ **PERINGATAN KERAMAT / HAZARD**: Cuaca Nightmare aktif! Kabut teror mimpi buruk menyelimuti dunia, monster makin buas!\n> *(Nightmare weather active! Abyssal horror fog covers the realm, stay alert)*",
    ["HeavyRain"]     = "⚠️ **PERINGATAN DINI / ADVISORY**: Hujan deres bray! Angkat jemuran sebelum emak ngamuk!\n> *(Torrential downpour! Bring laundry inside before mom gets mad)*",
    ["NormalRain"]    = "🌦️ **INFO BMKG / ADVISORY**: Hujan rintik-rintik, adem tapi bikin mager dan rawan galau.\n> *(Rainy and cozy, perfect weather to procrastinate and stay in bed)*",
    ["Rain"]          = "🌦️ **INFO BMKG / ADVISORY**: Hujan turun, tanah basah, sedia payung sebelum kuyup.\n> *(Light rain falling, grab an umbrella before you get soaked)*",
    ["Drizzle"]       = "🌦️ **INFO BMKG / ADVISORY**: Gerimis mengundang, tanaman auto-siram, tidur makin nyenyak.\n> *(Gentle drizzle active, crops auto-watered, sleep hits different)*",
    ["Dry"]           = "☀️ **INFO BMKG / ADVISORY**: Panas terik ada 9 matahari, aspal meleleh, rebahan depan kipas.\n> *(Blistering heatwave! 9 suns outside, stay indoors near the AC)*",
    ["Snow"]          = "❄️ **INFO BMKG / ADVISORY**: Dingin banget lur, sedingin sikap dia pas diajak jalan.\n> *(Freezing blizzard conditions! As cold as your crush's text replies)*",
    ["Windy"]         = "💨 **INFO BMKG / ADVISORY**: Angin sepoi kencang, ati-ati genteng tetangga terbang.\n> *(Gusty winds active! Watch out for flying rooftop tiles)*",
    ["Gale"]          = "🌪️ **PERINGATAN BMKG / WARNING**: Angin ribut kencang! Pegangan tiang atau pegangan tangan orang.\n> *(High wind storm! Hold onto something sturdy or get blown away)*",
    ["PortalEclipse"] = "🚨 **PERINGATAN KERAMAT / HAZARD**: Langit berdarah! Gerhana Portal Terbuka! Dunia sedang kacau!\n> *(Crimson skies! The Eclipse Portal is open! Chaos has begun)*"
}

-- Progress Bar Helper (Authentic Weather App Gauge)
local function makeProgressBar(ratio, length)
    length = length or 10
    local filled = math.clamp(math.floor(ratio * length + 0.5), 0, length)
    return string.rep("█", filled) .. string.rep("░", length - filled)
end

-- Exact Live In-Game Clock & Phase
local function getExactInGameTimeAndPhase()
    local now = os.time()
    local gmt7Time = now + TIMEZONE_OFFSET
    local secondsIntoDay = (gmt7Time - 3 * 3600) % 43200
    if secondsIntoDay < 0 then secondsIntoDay = secondsIntoDay + 43200 end
    
    local inGameTotalSeconds = secondsIntoDay * 2
    local inGameHour24 = math.floor(inGameTotalSeconds / 3600) % 24
    local inGameMinute = math.floor((inGameTotalSeconds % 3600) / 60)
    
    local period = inGameHour24 >= 12 and "PM" or "AM"
    local h12 = inGameHour24 % 12
    if h12 == 0 then h12 = 12 end
    
    local timeStr = string.format("%d:%02d %s", h12, inGameMinute, period)
    local isDay = (inGameHour24 >= 6 and inGameHour24 < 18)
    local phaseBadge = isDay and "☀️ Daytime" or "🌙 Nighttime"
    
    return timeStr, phaseBadge, (inGameHour24 + inGameMinute / 60)
end

-- Exact Duration Formatter
local function formatDurationHM(targetUnix)
    local rem = math.max(0, targetUnix - os.time())
    local d = math.floor(rem / 86400)
    local h = math.floor((rem % 86400) / 3600)
    local m = math.floor((rem % 3600) / 60)
    
    local dayStr = d == 1 and "1 day" or (d .. " days")
    local hrStr  = h == 1 and "1 hour" or (h .. " hours")
    
    if d > 0 then
        return string.format("%s %s (<t:%d:t>)", dayStr, hrStr, targetUnix)
    elseif h > 0 then
        return string.format("%s %d mins (<t:%d:t>)", hrStr, m, targetUnix)
    else
        return string.format("%d mins (<t:%d:t>)", m, targetUnix)
    end
end

-- ============================================================
-- 6. DYNAMIC WEATHER ODDS & MULTIPLIER FORMATTER
-- ============================================================

-- Dynamically discovers all registered weather keys
local function getAllRegisteredWeathers()
    local seen = {}
    local list = {}
    
    local function addKey(k)
        if k and not seen[k] then
            seen[k] = true
            table.insert(list, k)
        end
    end
    
    for k in pairs(EffectsTable) do addKey(k) end
    for k in pairs(DisplayNames) do addKey(k) end
    for k in pairs(FogSettings) do addKey(k) end
    
    -- Ensure standard baseline
    for _, k in ipairs({"Dry", "Drizzle", "NormalRain", "HeavyRain", "Snow", "Windy", "Gale", "NorthernLights", "Nightmare"}) do
        addKey(k)
    end
    
    return list
end

local function calculateWeatherOdds(season, day)
    local seasonPool = Probabilities[season]
    local dayPool = seasonPool and seasonPool[day] or {}

    local totalWeight = 0
    for _, weight in pairs(dayPool) do
        totalWeight = totalWeight + (tonumber(weight) or 0)
    end

    local trackedKeys = {}
    local sortedOdds = {}

    -- Process weathers in today's active pool
    for weatherKey, weight in pairs(dayPool) do
        trackedKeys[weatherKey] = true
        if weatherKey == "NormalRain" or weatherKey == "Rain" then
            trackedKeys["NormalRain"] = true
            trackedKeys["Rain"] = true
        end

        local wVal = tonumber(weight) or 0
        local pct = (totalWeight > 0) and ((wVal / totalWeight) * 100) or 0
        local dName = DisplayNames[weatherKey] or weatherKey
        local icon = WEATHER_ICONS[weatherKey] or "🌤️"
        table.insert(sortedOdds, { key = weatherKey, name = dName, icon = icon, pct = pct, weight = wVal })
    end

    -- Include other known weathers (0% odds)
    local allKnown = getAllRegisteredWeathers()
    for _, weatherKey in ipairs(allKnown) do
        if not trackedKeys[weatherKey] and weatherKey ~= "Rain" and weatherKey ~= "PortalEclipse" then
            trackedKeys[weatherKey] = true
            local dName = DisplayNames[weatherKey] or (weatherKey == "NormalRain" and "Rain" or weatherKey)
            local icon = WEATHER_ICONS[weatherKey] or "🌤️"
            table.insert(sortedOdds, { key = weatherKey, name = dName, icon = icon, pct = 0, weight = 0 })
        end
    end

    -- Sort descending: Highest chance first, 0% at the bottom
    table.sort(sortedOdds, function(a, b)
        if math.floor(a.pct + 0.5) ~= math.floor(b.pct + 0.5) then
            return a.pct > b.pct
        end
        return a.name < b.name
    end)

    return sortedOdds
end

-- Clean Multiplier Badges with V1 Upgrade/Mining metrics
local function formatWeatherAppEffects(effects, rawWeather)
    effects = effects or {}
    local lines = {}
    
    -- 1. Market & Shop Prices
    local priceVal = effects.PriceMultiplier or 1
    local pricePct = math.floor((priceVal - 1) * 100 + 0.5)
    if pricePct ~= 0 then
        local isBad = pricePct > 0
        local icon = isBad and "🔴" or "🟢"
        local note = isBad and (pricePct >= 20 and "Inflasi Ekstrem / Extreme Blizzard Gouging" or "Harga Naik / Price Surcharge") or "Diskon / Market Sale"
        table.insert(lines, string.format("🏷️ **Shop Prices:** %s `%+d%%` *(%s)*", icon, pricePct, note))
    else
        table.insert(lines, "🏷️ **Shop Prices:** 🟢 `Normal (1.0x)` *(Harga wajar / Standard prices)*")
    end
    
    -- 2. Combat Multipliers
    local dmgPct = math.floor(((effects.DamageMultiplier or 1) - 1) * 100 + 0.5)
    local spdPct = math.floor(((effects.MoveSpeedMultiplier or 1) - 1) * 100 + 0.5)
    local combatParts = {}
    if dmgPct ~= 0 then
        table.insert(combatParts, string.format("Damage `%+d%%` %s", dmgPct, dmgPct > 0 and "🟢" or "🔴"))
    else
        table.insert(combatParts, "Damage `Normal` 🟢")
    end
    if spdPct ~= 0 then
        table.insert(combatParts, string.format("Speed `%+d%%` %s", spdPct, spdPct > 0 and "🟢" or "🔴"))
    else
        table.insert(combatParts, "Speed `Normal` 🟢")
    end
    table.insert(lines, "⚔️ **Combat Multipliers:** " .. table.concat(combatParts, "  •  "))
    
    -- 3. Crafting, Mining & Economy (V1 Features)
    local craftParts = {}
    local upgradeBonus = effects.UpgradeSuccessBonus or (rawWeather == "NorthernLights" and 0.1 or 0)
    if WeatherController and WeatherController.GetUpgradeSuccessBonus then
        upgradeBonus = pcall(WeatherController.GetUpgradeSuccessBonus) and WeatherController.GetUpgradeSuccessBonus() or upgradeBonus
    end
    if upgradeBonus ~= 0 then
        table.insert(craftParts, string.format("Upgrade Success `+%d%%` 🟢", math.floor(upgradeBonus * 100 + 0.5)))
    end

    local miningSpeed = effects.MiningSpeedPct or (rawWeather == "Nightmare" and 10 or 0)
    if WeatherController and WeatherController.GetMiningSpeedPct then
        miningSpeed = pcall(WeatherController.GetMiningSpeedPct) and WeatherController.GetMiningSpeedPct() or miningSpeed
    end
    if miningSpeed ~= 0 then
        table.insert(craftParts, string.format("Mining Speed `%+d%%` 🟢", math.floor(miningSpeed + 0.5)))
    end

    local expPct = math.floor(((effects.EXPMultiplier or (rawWeather == "Nightmare" and 1.5 or 1)) - 1) * 100 + 0.5)
    if expPct ~= 0 then
        table.insert(craftParts, string.format("EXP Bonus `%+d%%` 🟢", expPct))
    end

    local dropPct = math.floor(((effects.DropLuck or (rawWeather == "Nightmare" and 1.5 or 1)) - 1) * 100 + 0.5)
    if dropPct ~= 0 then
        table.insert(craftParts, string.format("Monster Drops `%+d%%` 🟢", dropPct))
    end

    if rawWeather == "NorthernLights" or effects.LumenDrops then
        local lPct = effects.LumenDrops and math.floor(effects.LumenDrops * 100 + 0.5) or 100
        table.insert(craftParts, string.format("Lumen Drops `+%d%%` 🟢", lPct))
    end

    if rawWeather == "Nightmare" or effects.MineralChance then
        local mPct = effects.MineralChance and math.floor(effects.MineralChance * 100 + 0.5) or 10
        table.insert(craftParts, string.format("Mineral Chance `+%d%%` 🟢", mPct))
    end

    if #craftParts > 0 then
        table.insert(lines, "⚒️ **Gathering & Crafting:** " .. table.concat(craftParts, "  •  "))
    end
    
    -- 4. Environment & Ecology
    local envParts = {}
    if (effects.AutoWater or 0) > 0 then
        table.insert(envParts, "🌱 Auto-Water Crops `100%` 🟢")
    end
    if Constants.Fishing and Constants.Fishing.AllFishWeathers and Constants.Fishing.AllFishWeathers[rawWeather] then
        table.insert(envParts, "🎣 Universal Fish Biting `ACTIVE` 🟢")
    end
    if rawWeather == "PortalEclipse" then
        table.insert(envParts, "🟣 Shadow Mutations `ACTIVE (120s)`")
    end
    
    if #envParts > 0 then
        table.insert(lines, "🌿 **Ecology & Farming:** " .. table.concat(envParts, "  •  "))
    end

    return lines
end

local function getNextWeatherSlotUnix()
    local now = os.time()
    local gmt7Time = now + TIMEZONE_OFFSET
    local secondsIntoDay = (gmt7Time - 3 * 3600) % 43200
    if secondsIntoDay < 0 then secondsIntoDay = secondsIntoDay + 43200 end

    local slotIndex = math.floor(secondsIntoDay / WEATHER_SLOT_SECONDS) + 1
    local secondsInSlot = secondsIntoDay % WEATHER_SLOT_SECONDS
    local secondsRemainingInSlot = WEATHER_SLOT_SECONDS - secondsInSlot
    
    local slotRatio = math.clamp(secondsInSlot / WEATHER_SLOT_SECONDS, 0, 1)

    if secondsRemainingInSlot <= 30 then
        secondsRemainingInSlot = secondsRemainingInSlot + WEATHER_SLOT_SECONDS
        slotIndex = (slotIndex % 6) + 1
        slotRatio = 0
    end

    return now + secondsRemainingInSlot, slotIndex, slotRatio
end

-- ============================================================
-- 7. DISPATCHER & OFFLINE RECOVERY ENGINE
-- ============================================================

local savedSnapshot = loadSavedState() or {}
local lastMessageId = savedSnapshot.messageId
local lastRecordedWeather = savedSnapshot.weather or ""
local lastRecordedSeason = savedSnapshot.season or ""
local lastRecordedDay = savedSnapshot.day or 0
local lastRecordedSlot = savedSnapshot.slot or 0
local lastRecordedTimestamp = savedSnapshot.timestamp or 0
local currentActiveHeader = savedSnapshot.activeHeader or ""
local alertedMilestones = {}

local function sendForecast(statusMsg, targetRoleId, forceNewMessage)
    if not isCurrentInstance() then return end

    local state = Constants.GetSeasonState(os.time())
    local season = state.Season
    local day = state.SeasonDay or 1
    local cyclePos = state.CyclePosition or 0

    local seasonInfo = SEASONS_DATA[season] or { next = "Spring", endPos = 1.00, icon = "❄️", nextIcon = "🌱" }
    local nextSeasonName = seasonInfo.next
    local nextSeasonIcon = seasonInfo.nextIcon
    local currentSeasonIcon = seasonInfo.icon

    local remFraction = seasonInfo.endPos - cyclePos
    if remFraction < 0 then remFraction = remFraction + 1 end
    local secsUntilNextSeason = math.floor(remFraction * TOTAL_YEAR_CYCLE_SECONDS)
    local nextSeasonUnix = os.time() + secsUntilNextSeason
    
    -- Season Cycle Ratio (4 Days per season)
    local seasonRatio = math.clamp(((day - 1) + (1 - (secsUntilNextSeason % 172800) / 172800)) / 4, 0, 1)

    local nextRollUnix, slotIndex, slotRatio = getNextWeatherSlotUnix()
    local inGameTimeFormatted, dayNightPhase = getExactInGameTimeAndPhase()
    local targetInGameRollHour = SLOT_ROLL_HOURS[slotIndex] or "4:00 PM"

    local weatherData = NetworkController.GetLastWeatherData and NetworkController.GetLastWeatherData() or {}
    local rawWeather = weatherData.WeatherType or (WeatherController and pcall(WeatherController.GetWeatherType) and WeatherController.GetWeatherType()) or "Dry"
    local weatherDisplay = DisplayNames[rawWeather] or (rawWeather == "NormalRain" and "Rain" or rawWeather)
    local weatherIcon = WEATHER_ICONS[rawWeather] or "🌤️"
    local embedColor = WEATHER_COLORS[rawWeather] or 0x3498DB
    local bmkgQuote = BMKG_QUOTES[rawWeather] or ("📢 **INFO BMKG**: Current weather is " .. weatherDisplay .. ".")

    -- Active Atmospheric Telemetry (WeatherController V1 Integration)
    local rainInt, snowInt, windInt, cloudInt = 0, 0, 0, 0
    local isIndoors = false
    local stormIntensity = 0
    if WeatherController then
        pcall(function()
            if WeatherController.GetIntensities then
                rainInt, snowInt, windInt, cloudInt = WeatherController.GetIntensities()
            end
            if WeatherController.GetStormIntensity then
                stormIntensity = WeatherController.GetStormIntensity()
            end
            if WeatherController.IsIndoors then
                isIndoors = WeatherController.IsIndoors()
            end
        end)
    end
    
    -- If raw intensities not available, estimate based on active weather
    if rainInt == 0 and (rawWeather == "HeavyRain" or rawWeather == "NormalRain" or rawWeather == "Rain" or rawWeather == "Drizzle") then
        rainInt = (rawWeather == "HeavyRain" and 1.0) or (rawWeather == "Drizzle" and 0.3) or 0.6
    end
    if windInt == 0 and (rawWeather == "Gale" or rawWeather == "Windy") then
        windInt = (rawWeather == "Gale" and 1.0) or 0.5
    end
    if snowInt == 0 and rawWeather == "Snow" then
        snowInt = 0.8
    end

    local telemetryLines = {
        string.format("> 🌧️ **Rain:** `%.1f` %s  •  💨 **Wind:** `%.1f` %s", rainInt or 0, makeProgressBar(rainInt or 0, 5), windInt or 0, makeProgressBar(windInt or 0, 5)),
        string.format("> ❄️ **Snow:** `%.1f` %s  •  ⚡ **Storm Severity:** `%.0f%%` %s", snowInt or 0, makeProgressBar(snowInt or 0, 5), math.min(100, (stormIntensity or 0) * 100), makeProgressBar(math.min(1, stormIntensity or 0), 5)),
        string.format("> 📍 **Station Sensor:** `%s`", isIndoors and "Indoors / Sheltered 🏠" or "Open Sky / Outdoors 🏞️")
    }

    local formattedBuffs = formatWeatherAppEffects(weatherData.Effects, rawWeather)

    -- Bar-Chart Weather Odds (Interactive Weather App Forecast)
    local oddsList = calculateWeatherOdds(season, day)
    local oddsForecastLines = {}
    for _, odd in ipairs(oddsList) do
        local bar = makeProgressBar(odd.pct / 100, 8)
        table.insert(oddsForecastLines, string.format("`[%s]` **%2.0f%%** %s **%s**", bar, odd.pct, odd.icon, odd.name))
    end

    local portalTimestamp = tonumber(ReplicatedStorage:GetAttribute(Schedule.ClientAttribute)) or tonumber(ReplicatedStorage:GetAttribute("WeeklyBossStartEpoch"))
    local portalLine = nil
    if portalTimestamp then
        portalLine = string.format("> 🌀 **Gate Opening / Pembukaan:** %s\n> 🛡️ *Siapkan mental & gear terbaik! (Prepare your best potions & equipment!)*", formatDurationHM(portalTimestamp))
    end

    local slotBar = makeProgressBar(slotRatio, 8)
    local seasonBar = makeProgressBar(seasonRatio, 8)

    local fields = {
        {
            name = currentSeasonIcon .. " Current Season",
            value = string.format("**%s** (Day %d of 4)\n> **Next:** %s %s\n> **Starts:** %s\n> `[%s]` `%d%% Orbit`", 
                season, day, nextSeasonIcon, nextSeasonName, formatDurationHM(nextSeasonUnix), seasonBar, math.floor(seasonRatio * 100 + 0.5)),
            inline = true
        },
        {
            name = weatherIcon .. " Current Weather (" .. slotIndex .. "/6)",
            value = string.format("**%s** • `%s`\n> **In-Game:** `%s` *(Rolls at %s)*\n> **Next Roll:** %s\n> `[%s]` `%d%% Elapsed`", 
                weatherDisplay, dayNightPhase, inGameTimeFormatted, targetInGameRollHour, formatDurationHM(nextRollUnix), slotBar, math.floor(slotRatio * 100 + 0.5)),
            inline = true
        },
        {
            name = "🛰️ Live Atmosphere & Storm Telemetry",
            value = table.concat(telemetryLines, "\n"),
            inline = false
        },
        {
            name = "📊 Market & Adventurer Telemetry (Active Modifiers)",
            value = table.concat(formattedBuffs, "\n"),
            inline = false
        },
        {
            name = string.format("🎲 24H Weather Gacha Forecast (Day %d Pool)", day),
            value = table.concat(oddsForecastLines, "\n"),
            inline = false
        }
    }

    if portalLine then
        table.insert(fields, {
            name = "🌀 Dimensional Rift • Dewdrop Portal & Eclipse",
            value = portalLine,
            inline = false
        })
    end

    if targetRoleId then
        currentActiveHeader = string.format("📢 **%s!** <@&%s>", (statusMsg or "Weather Alert"), targetRoleId)
    elseif forceNewMessage then
        currentActiveHeader = ""
    end

    local shortJobId = string.sub(game.JobId ~= "" and game.JobId or "Online", 1, 8)
    local footerText = string.format("BMKG Observatory Station • Server: %s • Live Radar Sync", shortJobId)

    local payload = {
        content = currentActiveHeader,
        allowed_mentions = {
            roles = {
                "1557371108032913521",
                "1557371110193106954",
                "1557371112357367849",
                "1557371115024941056",
                "1557371120422883411",
                "1557371122318708857",
                "1557371124222787594",
                "1557371125971820554",
                "1557371127326572579",
                "1557371128920547460"
            }
        },
        embeds = {{
            title = "📡 Badan Meteorologi Klimatologi dan Gacha (BMKG)",
            description = bmkgQuote,
            color = embedColor,
            fields = fields,
            footer = { text = footerText },
            timestamp = DateTime.now():ToIsoDate()
        }}
    }

    local httpRequest = (syn and syn.request) or (http and http.request) or http_request or request
    if httpRequest and isCurrentInstance() then
        -- -------------------------------------------------------------
        -- CLOUD IMAGE GENERATOR BRIDGE (Fetches Anime Card from Render)
        -- -------------------------------------------------------------
        if CLOUD_API_URL and CLOUD_API_URL ~= "" then
            if lastCardUrl and lastCardWeather == rawWeather and not forceNewMessage then
                -- Weather hasn't changed; reuse cached image card to prevent redundant cloud generation every minute
                payload.embeds = {{
                    color = embedColor,
                    image = { url = lastCardUrl }
                }}
            else
                -- Collect readable modifiers list for card chips using exact scraped game Constants
                local modChips = {}
                local effects = weatherData.Effects or (Constants.Weather and Constants.Weather.Effects and Constants.Weather.Effects[rawWeather]) or {}

                -- 1. Shop Price Multipliers
                local pVal = effects.PriceMultiplier or 1
                local pPct = math.floor((pVal - 1) * 100 + 0.5)
                if pPct > 0 then
                    table.insert(modChips, string.format("Shop +%d%% (Surcharge)", pPct))
                elseif pPct < 0 then
                    table.insert(modChips, string.format("Shop %d%% Sale", pPct))
                end

                -- 2. Combat Multipliers (Damage & Speed)
                local dVal = effects.DamageMultiplier or 1
                local dPct = math.floor((dVal - 1) * 100 + 0.5)
                if dPct ~= 0 then
                    table.insert(modChips, string.format("Damage %+d%%", dPct))
                end

                local sVal = effects.MoveSpeedMultiplier or 1
                local sPct = math.floor((sVal - 1) * 100 + 0.5)
                if sPct ~= 0 then
                    table.insert(modChips, string.format("Speed %+d%%", sPct))
                end

                -- 3. Ecology & Auto-Water
                local wVal = effects.AutoWater or 0
                if wVal >= 1 then
                    table.insert(modChips, "Auto-Water Crops 100%")
                elseif wVal > 0 then
                    table.insert(modChips, string.format("Auto-Water Crops %d%%", math.floor(wVal * 100 + 0.5)))
                end

                -- 4. Special Bonuses (Upgrades, Mining, EXP, Monster Drops, Lumen)
                local upgVal = effects.UpgradeSuccessBonus or (rawWeather == "NorthernLights" and 10 or 0)
                if upgVal > 0 then
                    table.insert(modChips, string.format("Upgrade Success +%d%%", math.floor(upgVal + 0.5)))
                end

                local lumenVal = effects.LumenLuck or (rawWeather == "NorthernLights" and 2 or 1)
                if lumenVal > 1 then
                    table.insert(modChips, string.format("Lumen Luck %.0fx", lumenVal))
                end

                local mineVal = effects.MiningSpeedPct or (rawWeather == "Nightmare" and 10 or 0)
                if mineVal > 0 then
                    table.insert(modChips, string.format("Mining Speed +%d%%", math.floor(mineVal + 0.5)))
                end

                local minVal = effects.MineralChanceBonus or 0
                if minVal > 0 then
                    table.insert(modChips, string.format("Mineral Chance +%d%%", math.floor(minVal + 0.5)))
                end

                local expVal = effects.EXPMultiplier or 1
                if expVal > 1 then
                    table.insert(modChips, string.format("EXP Bonus +%d%%", math.floor((expVal - 1) * 100 + 0.5)))
                end

                local dropVal = effects.DropLuck or 1
                if dropVal > 1 then
                    table.insert(modChips, string.format("Monster Drops +%d%%", math.floor((dropVal - 1) * 100 + 0.5)))
                end

                -- 5. Dimensional Fishing & Shadow Mutations
                if rawWeather == "PortalEclipse" then
                    table.insert(modChips, "Shadow Mutation Active")
                    table.insert(modChips, "Universal Fish Biting")
                elseif rawWeather == "Nightmare" then
                    table.insert(modChips, "Ghost Mutation Active")
                end

                -- Fallback if no buffs
                if #modChips == 0 then
                    table.insert(modChips, "Shop 1.0x Normal (Standard Prices)")
                    table.insert(modChips, "Combat 1.0x Normal")
                end

                -- Simplified odds array for visual card
                local oddsTuples = {}
                for _, od in ipairs(oddsList) do
                    table.insert(oddsTuples, { od.name, od.key or od.name, od.pct })
                end

                local cloudPayload = {
                    weather_type = rawWeather,
                    weather_display = weatherDisplay,
                    season = season,
                    season_day = day,
                    slot_index = slotIndex,
                    server_id = shortJobId,
                    in_game_clock = inGameTimeFormatted,
                    target_roll_hour = targetInGameRollHour,
                    slot_progress = slotRatio,
                    storm_pct = stormIntensity or 0,
                    storm_level = string.format("%.0f%%", (stormIntensity or 0) * 100),
                    wind_force = string.format("%.1f", windInt or 0),
                    rain_index = string.format("%.1f", rainInt or 0),
                    indoor_status = isIndoors and "Indoors / Sheltered 🏠" or "Open Sky / Outdoors 🏞️",
                    active_modifiers = modChips,
                    portal_time_str = portalTimestamp and ("Gate Opening in " .. formatDurationHM(portalTimestamp)) or "Gate Opening in 2 days 10 hours",
                    odds = oddsTuples
                }

                print("[BMKG Cloud] 📡 Requesting Anime Weather Card from Cloud (" .. tostring(rawWeather) .. ")...")
                local cloudOk, cloudErr = pcall(function()
                    local cRes = httpRequest({
                        Url = string.gsub(CLOUD_API_URL, "/+$", "") .. "/api/card/upload",
                        url = string.gsub(CLOUD_API_URL, "/+$", "") .. "/api/card/upload",
                        Method = "POST",
                        method = "POST",
                        Headers = { ["Content-Type"] = "application/json" },
                        headers = { ["Content-Type"] = "application/json" },
                        Body = HttpService:JSONEncode(cloudPayload),
                        body = HttpService:JSONEncode(cloudPayload),
                        Timeout = 30,
                        timeout = 30
                    })
                    local resBody = cRes and (cRes.Body or cRes.body)
                    local resCode = cRes and (cRes.StatusCode or cRes.status or cRes.statusCode or 0)
                    if resBody then
                        local sDec, decData = pcall(HttpService.JSONDecode, HttpService, resBody)
                        if sDec and decData and decData.image_url then
                            print("[BMKG Cloud] ✅ Card successfully attached: " .. tostring(decData.image_url))
                            lastCardUrl = decData.image_url
                            lastCardWeather = rawWeather
                            -- Pure visual card presentation: render only the image card (removes text redundancy)
                            payload.embeds = {{
                                color = embedColor,
                                image = { url = decData.image_url }
                            }}
                            lastCloudPing = os.time()
                        else
                            print("[BMKG Cloud] ⚠️ Decode error or missing image_url (Code " .. tostring(resCode) .. "): " .. tostring(resBody))
                        end
                    else
                        print("[BMKG Cloud] ⚠️ Cloud returned no body (Code: " .. tostring(resCode) .. ")")
                    end
                end)
                if not cloudOk then
                    print("[BMKG Cloud] ❌ HTTP Exception: " .. tostring(cloudErr))
                end
            end
        end
            if forceNewMessage or targetRoleId then
                if lastMessageId then
                    pcall(function()
                        httpRequest({
                            Url = DISCORD_WEBHOOK .. "/messages/" .. tostring(lastMessageId),
                            Method = "DELETE"
                        })
                    end)
                    task.wait(0.5)
                end

                local response = httpRequest({
                    Url = DISCORD_WEBHOOK .. "?wait=true",
                    Method = "POST",
                    Headers = { ["Content-Type"] = "application/json" },
                    Body = HttpService:JSONEncode(payload)
                })

                if response and response.Body then
                    local successDecode, data = pcall(HttpService.JSONDecode, HttpService, response.Body)
                    if successDecode and data and data.id then
                        lastMessageId = data.id
                        saveState({
                            messageId = data.id,
                            weather = rawWeather,
                            season = season,
                            day = day,
                            slot = slotIndex,
                            activeHeader = currentActiveHeader,
                            timestamp = os.time()
                        })
                    end
                end
            else
                local patched = false
                if lastMessageId then
                    local patchResponse = httpRequest({
                        Url = DISCORD_WEBHOOK .. "/messages/" .. tostring(lastMessageId),
                        Method = "PATCH",
                        Headers = { ["Content-Type"] = "application/json" },
                        Body = HttpService:JSONEncode(payload)
                    })
                    if patchResponse and (patchResponse.StatusCode == 200 or patchResponse.statusCode == 200 or patchResponse.Status == 200) then
                        patched = true
                    end
                end

                -- Fallback to POST only if PATCH failed and we haven't already posted recently for this exact weather
                if not patched then
                    local response = httpRequest({
                        Url = DISCORD_WEBHOOK .. "?wait=true",
                        Method = "POST",
                        Headers = { ["Content-Type"] = "application/json" },
                        Body = HttpService:JSONEncode(payload)
                    })
                    if response and response.Body then
                        local successDecode, data = pcall(HttpService.JSONDecode, HttpService, response.Body)
                        if successDecode and data and data.id then
                            lastMessageId = data.id
                            saveState({
                                messageId = data.id,
                                weather = rawWeather,
                                season = season,
                                day = day,
                                slot = slotIndex,
                                activeHeader = currentActiveHeader,
                                timestamp = os.time()
                            })
                        end
                    end
                end
            end
        end
    end

-- ============================================================
-- 8. EVENT LISTENER & ACTIVE WATCHDOG LOOP
-- ============================================================

local function handleWeatherTransition(newWeather)
    if newWeather ~= lastRecordedWeather then
        print(string.format("[BMKG] 🌦️ Live Weather Transition Detected: %s -> %s", tostring(lastRecordedWeather), tostring(newWeather)))
        lastRecordedWeather = newWeather
        local isEclipse = (newWeather == "PortalEclipse")
        local alertText = isEclipse and "🚨 GERHANA PORTAL KERAMAT AKTIF! (ECLIPSE HAZARD)" or ("Perubahan Cuaca / Weather Change: " .. tostring(DisplayNames[newWeather] or newWeather))
        
        -- Smart Role Mapping (matches exact role or checks price impact)
        local targetRole = WEATHER_ROLES[newWeather]
        if not targetRole and EffectsTable[newWeather] then
            local pm = EffectsTable[newWeather].PriceMultiplier or 1
            if pm >= 1.20 then
                targetRole = WEATHER_ROLES["Snow"]
            elseif pm >= 1.10 then
                targetRole = WEATHER_ROLES["HeavyRain"]
            elseif pm >= 1.05 then
                targetRole = WEATHER_ROLES["NormalRain"]
            end
        end
        
        sendForecast(alertText, targetRole, true)
    end
end

local weatherConn = NetworkController.OnWeatherUpdate:Connect(function(data)
    if not isCurrentInstance() then return end
    task.wait(0.5)
    local raw = data and data.WeatherType or "Dry"
    handleWeatherTransition(raw)
end)
table.insert(activeConnections, weatherConn)

task.spawn(function()
    task.wait(2)
    if not isCurrentInstance() then return end
    
    local initialData = NetworkController.GetLastWeatherData and NetworkController.GetLastWeatherData() or {}
    local currentLiveWeather = initialData.WeatherType or (WeatherController and pcall(WeatherController.GetWeatherType) and WeatherController.GetWeatherType()) or "Dry"
    local initialSeasonState = Constants.GetSeasonState(os.time())
    local currentLiveSeason = initialSeasonState.Season
    local currentLiveDay = initialSeasonState.SeasonDay or 1
    local _, currentLiveSlot = getNextWeatherSlotUnix()
    
    local isGapDetected = false
    if not savedSnapshot.messageId then
        isGapDetected = true
    elseif (os.time() - lastRecordedTimestamp) > 7200 then
        isGapDetected = true
    elseif currentLiveSeason ~= lastRecordedSeason or currentLiveDay ~= lastRecordedDay or currentLiveSlot ~= lastRecordedSlot or currentLiveWeather ~= lastRecordedWeather then
        isGapDetected = true
    end

    if isGapDetected then
        print("[BMKG] ⚠️ Information Gap / Re-sync Detected! Triggering live role update...")
        lastRecordedWeather = currentLiveWeather
        lastRecordedSeason = currentLiveSeason
        local alertText = (currentLiveWeather == "PortalEclipse") and "🚨 GERHANA PORTAL KERAMAT AKTIF! (ECLIPSE HAZARD)" or ("Radar Online & Re-synced: " .. tostring(DisplayNames[currentLiveWeather] or currentLiveWeather))
        local targetRole = WEATHER_ROLES[currentLiveWeather]
        sendForecast(alertText, targetRole, true)
    else
        print("[BMKG] ✓ Server hop within same active slot. Resuming silently.")
        sendForecast(nil, nil, false)
    end

    pcall(function()
        StarterGui:SetCore("SendNotification", {
            Title = "BMKG Radar Active",
            Text = "Radar connected to Server: " .. string.sub(game.JobId ~= "" and game.JobId or "Local", 1, 8),
            Duration = 5
        })
    end)

    while isCurrentInstance() do
        task.wait(60)
        if not isCurrentInstance() then break end

        local liveWeatherData = NetworkController.GetLastWeatherData and NetworkController.GetLastWeatherData() or {}
        local liveWeather = liveWeatherData.WeatherType or (WeatherController and pcall(WeatherController.GetWeatherType) and WeatherController.GetWeatherType()) or "Dry"
        if liveWeather ~= lastRecordedWeather then
            handleWeatherTransition(liveWeather)
        else
            local currentSeasonState = Constants.GetSeasonState(os.time())
            if currentSeasonState.Season ~= lastRecordedSeason then
                lastRecordedSeason = currentSeasonState.Season
                sendForecast("Pergantian Musim / Season Change: " .. tostring(currentSeasonState.Season), nil, true)
            end

            local portalTimestamp = tonumber(ReplicatedStorage:GetAttribute(Schedule.ClientAttribute)) or tonumber(ReplicatedStorage:GetAttribute("WeeklyBossStartEpoch"))
            if portalTimestamp then
                local remSecs = portalTimestamp - os.time()
                local remMins = remSecs / 60

                local milestones = {
                    { 60, "⚠️ Peringatan Portal / Alert: 1 Jam / 1 Hour to Dewdrop Portal & Eclipse!" },
                    { 30, "⚠️ Peringatan Portal / Alert: 30 Menit / 30 Mins to Dewdrop Portal & Eclipse!" },
                    { 15, "🚨 Peringatan Portal / Alert: 15 Menit Lagi / 15 Mins Remaining! Gather at the Gate!" },
                    { 0,  "🌀 GERBANG PORTAL DEWDROP & ECLIPSE RESMI DIBUKA / PORTAL IS OPEN!" }
                }

                for _, m in ipairs(milestones) do
                    if remMins <= m[1] and remMins > (m[1] - 5) and not alertedMilestones[m[1]] then
                        alertedMilestones[m[1]] = true
                        sendForecast(m[2], ECLIPSE_ROLE_ID, true)
                        break
                    end
                end
            end

            -- Keepalive Heartbeat: Ping Cloud Server every 7 minutes to prevent Render free instance sleep
            if CLOUD_API_URL and CLOUD_API_URL ~= "" and (os.time() - lastCloudPing) >= 420 then
                pcall(function()
                    httpRequest({
                        Url = string.gsub(CLOUD_API_URL, "/+$", "") .. "/",
                        Method = "GET"
                    })
                    lastCloudPing = os.time()
                end)
            end

            sendForecast(nil, nil, false)
        end
    end
end)

print("[BMKG Lazie] 24/7 Portal Observatory Radar Master Edition V2 Active!")
