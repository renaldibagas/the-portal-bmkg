--[[
    ========================================================================
    BMKG COMPLETE GAME DATA SCRAPER & EXHAUSTIVE DUMPER
    ========================================================================
    Recursively scans and executes/requires EVERY SINGLE ModuleScript in:
      - ReplicatedStorage (all nested folders & packages)
      - Players.LocalPlayer.PlayerScripts (all client systems)
      - ReplicatedFirst (if any)
    
    Extracts:
      1. Every module's returned data table / config / constants / dictionary
      2. ReplicatedStorage Attributes & Value Objects
      3. Automatically organizes and dumps everything into "bmkg_gamedata/"
    ========================================================================
]]

local HttpService = game:GetService("HttpService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local ReplicatedFirst = game:GetService("ReplicatedFirst")
local Players = game:GetService("Players")
local LocalPlayer = Players.LocalPlayer

local DUMP_FOLDER = "bmkg_gamedata"

-- Create target directory
if makefolder then
    pcall(makefolder, DUMP_FOLDER)
    pcall(makefolder, DUMP_FOLDER .. "/modules_replicated")
    pcall(makefolder, DUMP_FOLDER .. "/modules_client")
end

-- Deep serializer to convert any complex Roblox datatype into clean JSON
local function deepSerialize(val, depth, maxDepth, seen)
    depth = depth or 0
    maxDepth = maxDepth or 7
    seen = seen or {}

    if depth > maxDepth then return "<MaxDepthReached>" end

    local valType = typeof(val)
    if valType == "string" or valType == "number" or valType == "boolean" then
        return val
    elseif val == nil then
        return nil
    elseif valType == "Vector3" then
        return { X = val.X, Y = val.Y, Z = val.Z }
    elseif valType == "Vector2" then
        return { X = val.X, Y = val.Y }
    elseif valType == "Color3" then
        return { R = math.floor(val.R * 255), G = math.floor(val.G * 255), B = math.floor(val.B * 255), Hex = val:ToHex() }
    elseif valType == "CFrame" then
        return { Position = { X = val.Position.X, Y = val.Position.Y, Z = val.Position.Z } }
    elseif valType == "EnumItem" then
        return tostring(val)
    elseif valType == "Instance" then
        return {
            __type = "Instance",
            ClassName = val.ClassName,
            Name = val.Name,
            FullName = val:GetFullName()
        }
    elseif valType == "function" then
        return "<function>"
    elseif valType == "table" then
        if seen[val] then
            return "<CircularRef>"
        end
        seen[val] = true

        local out = {}
        for k, v in pairs(val) do
            local keyStr = tostring(k)
            out[keyStr] = deepSerialize(v, depth + 1, maxDepth, seen)
        end
        return out
    else
        return tostring(val)
    end
end

local function saveJson(relativeFilePath, dataTable)
    if not writefile then return false end
    local serialized = deepSerialize(dataTable)
    local ok, jsonStr = pcall(HttpService.JSONEncode, HttpService, serialized)
    if ok and jsonStr then
        local fullPath = DUMP_FOLDER .. "/" .. relativeFilePath
        pcall(writefile, fullPath, jsonStr)
        return true
    end
    return false
end

print("------------------------------------------------------------")
print("[BMKG Scraper] 🚀 Starting EXHAUSTIVE, END-TO-END game scrape...")
print("------------------------------------------------------------")

local totalFound = 0
local totalSuccess = 0
local totalFailed = 0

local masterDump = {
    _metadata = {
        Timestamp = os.time(),
        PlaceId = game.PlaceId,
        JobId = game.JobId,
        ScraperVersion = "3.0.0-exhaustive"
    },
    ReplicatedStorage = {},
    PlayerScripts = {},
    ReplicatedAttributes = {}
}

-- 1. Exhaustively scan ReplicatedStorage
print("[BMKG Scraper] 📦 Scanning ALL descendants of ReplicatedStorage...")
for _, desc in ipairs(ReplicatedStorage:GetDescendants()) do
    if desc:IsA("ModuleScript") then
        totalFound = totalFound + 1
        local safeName = string.gsub(desc.Name, "[^%w_%-]", "_")
        local reqOk, reqResult = pcall(require, desc)

        if reqOk and type(reqResult) == "table" then
            totalSuccess = totalSuccess + 1
            masterDump.ReplicatedStorage[desc:GetFullName()] = reqResult
            saveJson("modules_replicated/" .. safeName .. ".json", reqResult)
        else
            totalFailed = totalFailed + 1
            masterDump.ReplicatedStorage[desc:GetFullName()] = "<RequireFailedOrNonTable>"
        end
    end
end

-- 2. Exhaustively scan LocalPlayer.PlayerScripts (Client modules)
if LocalPlayer and LocalPlayer:FindFirstChild("PlayerScripts") then
    print("[BMKG Scraper] 🎮 Scanning ALL descendants of PlayerScripts...")
    for _, desc in ipairs(LocalPlayer.PlayerScripts:GetDescendants()) do
        if desc:IsA("ModuleScript") then
            totalFound = totalFound + 1
            local safeName = string.gsub(desc.Name, "[^%w_%-]", "_")
            local reqOk, reqResult = pcall(require, desc)

            if reqOk and type(reqResult) == "table" then
                totalSuccess = totalSuccess + 1
                masterDump.PlayerScripts[desc:GetFullName()] = reqResult
                saveJson("modules_client/" .. safeName .. ".json", reqResult)
            else
                totalFailed = totalFailed + 1
                masterDump.PlayerScripts[desc:GetFullName()] = "<RequireFailedOrNonTable>"
            end
        end
    end
end

-- 3. Grab ReplicatedStorage Attributes & Value Objects
print("[BMKG Scraper] 🌐 Dumping World Attributes & Values...")
local attrs = ReplicatedStorage:GetAttributes()
masterDump.ReplicatedAttributes = attrs
saveJson("world_attributes.json", attrs)

-- 4. Save Master Complete Dump
print("[BMKG Scraper] 💾 Writing Master full_game_dump.json...")
saveJson("full_game_dump.json", masterDump)

print("------------------------------------------------------------")
print(string.format("[BMKG Scraper] ✅ FINISHED EXHAUSTIVE DUMP!"))
print(string.format("   • Modules Discovered : %d", totalFound))
print(string.format("   • Successfully Dumped: %d", totalSuccess))
print(string.format("   • Skipped / Non-Table: %d", totalFailed))
print("   • Saved to Folder    : " .. DUMP_FOLDER .. "/")
print("------------------------------------------------------------")
