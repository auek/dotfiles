local M = {}

-- Used if the optional local fortune command is missing or fails.
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

local function wrap_quote(quote)
  local lines = {}
  for _, paragraph in ipairs(vim.split(vim.trim(quote), "\n", { plain = true })) do
    local line = ""
    for word in paragraph:gmatch("%S+") do
      if line ~= "" then
        if vim.fn.strdisplaywidth(line .. " " .. word) > 52 then
          lines[#lines + 1], line = line, ""
        else
          line = line .. " "
        end
      end
      -- Split unusually long words too, without cutting UTF-8 characters.
      for _, char in ipairs(vim.fn.split(word, [[\zs]])) do
        if vim.fn.strdisplaywidth(line .. char) > 52 then
          lines[#lines + 1], line = line, ""
        end
        line = line .. char
      end
    end
    lines[#lines + 1] = line
  end
  -- A pathological fortune should not push all dashboard actions off screen.
  if #lines > 8 then return nil end
  return table.concat(lines, "\n")
end

local function cow_output(result)
  local output = result.stdout or ""
  if result.code ~= 0 or #output > 4096 or vim.trim(output) == "" then return nil end
  output = output:gsub("\n+$", "")
  local lines = vim.split(output, "\n", { plain = true })
  if #lines > 15 then return nil end
  for _, line in ipairs(lines) do
    if vim.fn.strdisplaywidth(line) > 56 then return nil end
  end
  return output
end

local function fallback_cow(text)
  local lines, width = vim.split(text, "\n", { plain = true }), 0
  for _, line in ipairs(lines) do width = math.max(width, vim.fn.strdisplaywidth(line)) end
  local bubble = { " " .. string.rep("_", width + 2) }
  for row, line in ipairs(lines) do
    local left, right = "<", ">"
    if #lines > 1 then
      left = row == 1 and "/" or row == #lines and "\\" or "|"
      right = row == 1 and "\\" or row == #lines and "/" or "|"
    end
    bubble[#bubble + 1] = left .. " " .. line .. string.rep(" ", width - vim.fn.strdisplaywidth(line)) .. " " .. right
  end
  bubble[#bubble + 1] = " " .. string.rep("-", width + 2)
  return table.concat(bubble, "\n") .. "\n" .. [[
        \   ^__^
         \  (oo)\_______
            (__)\       )\/\
                ||----w |
                ||     ||]]
end

local function pad_header(text)
  local lines = vim.split(text, "\n", { plain = true })
  while #lines < 15 do lines[#lines + 1] = "" end
  return table.concat(lines, "\n")
end

local function header(self)
  if not self._dotfiles_fortune then
    -- Reserve the final height before any jobs finish, keeping actions stationary.
    local state = { header = pad_header("") }
    self._dotfiles_fortune = state
    local function active()
      return vim.api.nvim_buf_is_valid(self.buf) and vim.api.nvim_win_is_valid(self.win)
        and vim.api.nvim_win_get_buf(self.win) == self.buf
    end
    local function finish(output)
      if state.done then return end
      state.done, state.header = true, pad_header(output)
      -- Publish only the final result. Never replace a file opened in the meantime.
      if active() then self:update() end
    end
    local function render_quote(text)
      if not active() or state.done then return end
      local fallback = fallback_cow(text)
      if vim.fn.executable("cowsay") == 1 then
        -- Try one random animal with our UTF-8-safe wrapping and no shell parsing.
        local ok = pcall(vim.system, { "cowsay", "-n", "-r" },
          { stdin = text, text = true, timeout = 300 }, vim.schedule_wrap(function(result)
            finish(cow_output(result) or fallback)
          end))
        if ok then return end
      end
      finish(fallback)
    end
    -- Start only for a rendered dashboard, after its blank header is in place.
    vim.schedule(function()
      if not active() then return end
      local fallback = wrap_quote(quotes[os.time() % #quotes + 1])
      if vim.fn.executable("fortune") == 1 then
        local started = pcall(vim.system, { "fortune", "-s" }, { text = true, timeout = 300 },
          vim.schedule_wrap(function(result)
            local text = result.stdout or ""
            local ok, wrapped = false, nil
            if result.code == 0 and #text <= 4096 and vim.trim(text) ~= "" then
              ok, wrapped = pcall(wrap_quote, text)
            end
            render_quote(ok and wrapped or fallback)
          end))
        if started then return end
      end
      render_quote(fallback)
    end)
  end
  return { header = self._dotfiles_fortune.header, padding = 1 }
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
      -- No Nerd Font dependency, including the automatically generated file list.
      formats = { header = { "%s", align = "left" }, icon = { "", width = 0 } },
      sections = {
        header,
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
