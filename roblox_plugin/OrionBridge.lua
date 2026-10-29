-- ORION Studio bridge. Install in Roblox/Plugins and enable HTTP requests.
-- Local queue protocol matches the supplied Python roblox_bridge.py.
local Http = game:GetService("HttpService")
local AssetService = game:GetService("AssetService")
local History = game:GetService("ChangeHistoryService")
local BASE = "http://127.0.0.1:8787"
local toolbar = plugin:CreateToolbar("ORION")
local toggle = toolbar:CreateButton("OrionBridge", "ORION bağlantısını aç / bağla", "")
local enabled = false

local function vector(values, fallback)
    if type(values) ~= "table" or #values ~= 3 then return fallback end
    return Vector3.new(tonumber(values[1]) or 0, tonumber(values[2]) or 0, tonumber(values[3]) or 0)
end

local function resolve(path)
    local current = game
    for name in string.gmatch(path or "Workspace", "[^%.]+") do
        if name == "game" then continue end
        current = current:FindFirstChild(name) or (name == "Workspace" and workspace)
        if not current then error("Parent tapılmadı: " .. tostring(path)) end
    end
    return current
end

local function execute(command)
    local p = command.params or {}
    local created
    if command.type == "create_part" then
        created = Instance.new("Part")
        created.Name = p.name or "OrionPart"
        created.Shape = ({ball = Enum.PartType.Ball, cylinder = Enum.PartType.Cylinder})[p.shape] or Enum.PartType.Block
        created.Size = vector(p.size, Vector3.new(2, 2, 2))
        created.Position = vector(p.position, Vector3.new(0, 5, 0))
        created.Anchored = p.anchored ~= false
        local color = p.color or {160, 130, 240}
        created.Color = Color3.fromRGB(math.clamp(tonumber(color[1]) or 160, 0, 255), math.clamp(tonumber(color[2]) or 130, 0, 255), math.clamp(tonumber(color[3]) or 240, 0, 255))
        created.Parent = resolve(p.parent)
    elseif command.type == "insert_script" then
        local kind = ({Script = true, LocalScript = true, ModuleScript = true})[p.script_type] and p.script_type or "Script"
        created = Instance.new(kind)
        created.Name = p.name or "OrionScript"
        created.Source = tostring(p.source or "")
        created.Parent = resolve(p.parent)
    elseif command.type == "create_ui" then
        created = Instance.new("ScreenGui")
        created.Name = p.name or "OrionUI"
        created.ResetOnSpawn = false
        for _, element in ipairs(p.elements or {}) do
            if not ({TextButton = true, TextLabel = true, Frame = true})[element.type] then error("UI növü dəstəklənmir") end
            local ui = Instance.new(element.type)
            ui.Size = UDim2.fromOffset(tonumber(element.width) or 200, tonumber(element.height) or 50)
            ui.Position = UDim2.fromOffset(tonumber(element.x) or 0, tonumber(element.y) or 0)
            if ui:IsA("TextLabel") or ui:IsA("TextButton") then ui.Text = tostring(element.text or "") end
            ui.Parent = created
        end
        created.Parent = game:GetService("StarterGui")
    elseif command.type == "weld" then
        local a, b = workspace:FindFirstChild(p.part_a, true), workspace:FindFirstChild(p.part_b, true)
        if not a or not b or not a:IsA("BasePart") or not b:IsA("BasePart") then error("Weld üçün hissələr tapılmadı") end
        created = Instance.new("WeldConstraint")
        created.Part0, created.Part1, created.Parent = a, b, a
    elseif command.type == "insert_mesh" then
        local id = tostring(p.asset_id or ""):match("(%d+)")
        if not id then error("Mesh asset ID düzgün deyil") end
        created = AssetService:CreateMeshPartAsync(Content.fromUri("rbxassetid://" .. id), {})
        created.Name = p.name or "OrionMesh"
        created.Position = vector(p.position, Vector3.new(0, 5, 0))
        if type(p.size) == "table" then created.Size = vector(p.size, created.Size) end
        created.Anchored = p.anchored ~= false
        created.Parent = resolve(p.parent)
    else
        error("Naməlum ORION əmri")
    end
    return {status = "ok", created = created:GetFullName()}
end

toggle.Click:Connect(function()
    enabled = not enabled
    toggle:SetActive(enabled)
    print(enabled and "[OrionBridgePlugin] işə düşdü..." or "[OrionBridgePlugin] dayandı.")
end)

plugin.Unloading:Connect(function() enabled = false end)

task.spawn(function()
    while true do
        task.wait(1)
        if not enabled then continue end
        local ok, payload = pcall(function() return Http:JSONDecode(Http:GetAsync(BASE .. "/queue", true)) end)
        if not ok then continue end
        for _, command in ipairs(payload.commands or {}) do
            History:SetWaypoint("ORION əməliyyatından əvvəl")
            local success, result = pcall(execute, command)
            if success then History:SetWaypoint("ORION əməliyyatından sonra") end
            pcall(function()
                Http:PostAsync(BASE .. "/result", Http:JSONEncode({id = command.id, result = success and result or {status = "error", message = tostring(result)}}), Enum.HttpContentType.ApplicationJson)
            end)
        end
    end
end)
