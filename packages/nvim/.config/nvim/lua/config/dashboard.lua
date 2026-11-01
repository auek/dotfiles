local M = {}

-- A small built-in fortune collection keeps startup offline and subprocess-free.
local quotes = {
  "Simplicity is prerequisite for reliability.",
  "Make it work, make it right, make it fast.",
  "A good beginning is half the work.",
  "There is no place like 127.0.0.1.",
  "Small steps still move you forward.",
  "The best error message is the one you never see.",
  "When in doubt, take a break.",
  "Save early. Commit often. Pet the cow.",
}

local function cow()
  local quote = quotes[os.time() % #quotes + 1]
  return " " .. string.rep("_", #quote + 2) .. "\n< " .. quote .. " >\n "
    .. string.rep("-", #quote + 2) .. "\n" .. [[
        \   ^__^
         \  (oo)\_______
            (__)\       )\/\
                ||----w |
                ||     ||]]
end

local function shortcuts()
  local items = {}
  -- Reuse the real mappings, including their descriptions and missing-tool guards.
  -- The final letter of ff/fg/fo/fe becomes the dashboard-only shortcut.
  for _, mapping in ipairs({ "<leader>ff", "<leader>fg", "<leader>fo", "<leader>fe" }) do
    local resolved = mapping:gsub("<leader>", vim.g.mapleader)
    local map = vim.fn.maparg(resolved, "n", false, true)
    items[#items + 1] = { key = mapping:sub(-1), desc = map.desc, action = mapping }
  end
  items[#items + 1] = { key = "n", desc = "New buffer", action = ":enew | startinsert" }
  items[#items + 1] = { key = "q", desc = "Quit", action = "<leader>q" }
  return items
end

function M.highlights()
  -- Register dashboard defaults first, then replace their loud UI accents with
  -- semantic theme links. Snacks reapplies these links on ColorScheme changes.
  require("snacks.dashboard")
  require("snacks.util").set_hl({
    Header = "String",
    Title = "String",
    Desc = "Normal",
    File = "Normal",
    Key = "Identifier",
    Dir = "Comment",
  }, { prefix = "SnacksDashboard" })
end

function M.options()
  return {
    dashboard = {
      enabled = true,
      width = 56,
      preset = { header = cow() },
      -- No Nerd Font dependency, including the automatically generated file list.
      formats = { header = { "%s", align = "left" }, icon = { "", width = 0 } },
      sections = {
        { section = "header", padding = 1 },
        function()
          return { title = vim.fn.fnamemodify(vim.fn.getcwd(), ":~"), align = "center", padding = 1 }
        end,
        shortcuts,
        { title = "Recent in this directory", section = "recent_files", cwd = true, limit = 5, padding = { 0, 1 } },
      },
    },
  }
end

return M
