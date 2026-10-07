--[[
    ========================================================================
    BMKG GAME DATA DUMPER / SCRAPER
    ========================================================================
    Dumps all game data (Constants, Weather, Fishing, Mining, Crafting, 
    Items, Shops, Drops, Configs) into a structured folder on your executor:
    
    Folder: "bmkg_gamedata/"
    Files:
      - bmkg_gamedata/constants_weather.json
      - bmkg_gamedata/constants_seasons.json
      - bmkg_gamedata/constants_fishing.json
      - bmkg_gamedata/constants_bosses.json
      - bmkg_gamedata/constants_all_raw.json
      - bmkg_gamedata/replicated_attributes.json
      - bmkg_gamedata/client_modules_list.json
      - bmkg_gamedata/full_game_dump.json
    ========================================================================
]]

local HttpService = game:GetService("HttpService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Players = game:GetService("Players")
local LocalPlayer = Players.LocalPlayer

local DUMP_FOLDER = "bmkg_gamedata"

-- Ensure writefile / makefolder exist
local canWrite = (writefile ~= nil)
local canMakeFolder = (makefolder ~= nil)

if canMakeFolder then
    pcall(makefolder, DUMP_FOLDER)
end

local function safeSerialize(val, depth, maxDepth)
    depth = depth or 0
    maxDepth = maxDepth or 6
    if depth > maxDepth then return "<MaxDepthReached>" end

    local valType = typeof(val)
    if valType == "string" or valType == "number" or valType == "boolean" then
        return val
    elseif valType == "Vector3" then
        return { X = val.X, Y = val.Y, Z = val.Z }
    elseif valType == "Color3" then
        return { R = val.R, G = val.G, B = val.B }
    elseif valType == "Instance" then
        return "<Instance: " .. val:GetFullName() .. ">"
    elseif valType == "function" then
        return "<function>"
    elseif valType == "table" then
        local out = {}
        for k, v in pairs(val) do
            local keyStr = tostring(k)
            out[keyStr] = safeSerialize(v, depth + 1, maxDepth)
        end
        return out
    else
        return tostring(val)
    end
end

local function dumpToFile(fileName, dataTable)
    local serialized = safeSerialize(dataTable)
    local success, jsonStr = pcall(HttpService.JSONEncode, HttpService, serialized)
    if success and jsonStr then
        local filePath = DUMP_FOLDER .. "/" .. fileName
        if writefile then
            pcall(writefile, filePath, jsonStr)
            print("[BMKG Dumper] ✅ Saved: " .. filePath)
        else
            warn("[BMKG Dumper] writefile not available on executor!")
        end
    else
        warn("[BMKG Dumper] JSON encoding failed for: " .. fileName)
    end
end

print("[BMKG Dumper] 🚀 Starting complete game data scrape...")

local fullDump = {}

-- 1. Constants Module
pcall(function()
    local Shared = ReplicatedStorage:FindFirstChild("Shared")
    if Shared then
        local Core = Shared:FindFirstChild("Core")
        if Core then
            local ConstModule = Core:FindFirstChild("Constants")
            if ConstModule and ConstModule:IsA("ModuleScript") then
                local Constants = require(ConstModule)
                if Constants then
                    fullDump["Constants"] = Constants
                    if Constants.Weather then
                        dumpToFile("constants_weather.json", Constants.Weather)
                    end
                    if Constants.Seasons or Constants.GetSeasonState then
                        dumpToFile("constants_seasons.json", {
                            Seasons = Constants.Seasons,
                            SeasonalProbabilities = Constants.Weather and Constants.Weather.SeasonalProbabilities
                        })
                    end
                    if Constants.Fishing then
                        dumpToFile("constants_fishing.json", Constants.Fishing)
                    end
                    if Constants.WeeklyBoss then
                        dumpToFile("constants_bosses.json", Constants.WeeklyBoss)
                    end
                    dumpToFile("constants_all_raw.json", Constants)
                end
            end
        end
    end
end)

-- 2. ReplicatedStorage Attributes
pcall(function()
    local attrs = ReplicatedStorage:GetAttributes()
    fullDump["ReplicatedAttributes"] = attrs
    dumpToFile("replicated_attributes.json", attrs)
end)

-- 3. Discover all ModuleScripts in ReplicatedStorage and Client
pcall(function()
    local moduleList = {}
    for _, desc in ipairs(ReplicatedStorage:GetDescendants()) do
        if desc:IsA("ModuleScript") then
            table.insert(moduleList, {
                Name = desc.Name,
                FullName = desc:GetFullName(),
                Parent = desc.Parent.Name
            })
        end
    end
    dumpToFile("modules_replicated.json", moduleList)
end)

-- 4. Try loading other common system configs if present
pcall(function()
    local extraConfigs = {}
    local Shared = ReplicatedStorage:FindFirstChild("Shared")
    if Shared then
        for _, child in ipairs(Shared:GetChildren()) do
            if child:IsA("ModuleScript") and child.Name ~= "Constants" then
                local ok, res = pcall(require, child)
                if ok and type(res) == "table" then
                    extraConfigs[child.Name] = res
                end
            end
        end
    end
    if next(extraConfigs) then
        dumpToFile("shared_modules_dump.json", extraConfigs)
        fullDump["SharedModules"] = extraConfigs
    end
end)

-- 5. Master Full Dump
dumpToFile("full_game_dump.json", fullDump)

print("[BMKG Dumper] 🎉 Complete! All scraped files are saved in folder: " .. DUMP_FOLDER .. "/")
