local M = {}

-- Used immediately, and retained if the optional local fortune command fails.
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

local function header(self)
  if not self._dotfiles_fortune then
    local state = {}
    self._dotfiles_fortune = state
    local function refresh()
      -- A late result must never move the cursor or replace an opened file.
      if vim.api.nvim_buf_is_valid(self.buf) and vim.api.nvim_win_is_valid(self.win)
          and vim.api.nvim_win_get_buf(self.win) == self.buf then
        self:update()
      end
    end
    local function set_quote(text)
      state.quote, state.header = text, text
      if vim.fn.executable("cowsay") ~= 1 then return end
      -- Keep our display-width-aware wrapping, including Unicode and long words.
      -- stdin avoids shell interpretation and quotes being treated as options.
      pcall(vim.system, { "cowsay", "-n", "-r" }, { stdin = text, text = true, timeout = 300 },
        vim.schedule_wrap(function(result)
          if state.quote ~= text or result.code ~= 0 then return end
          local output = result.stdout or ""
          if #output > 4096 or vim.trim(output) == "" then return end
          output = output:gsub("\n+$", "")
          local lines = vim.split(output, "\n", { plain = true })
          if #lines > 15 then return end
          for _, line in ipairs(lines) do
            if vim.fn.strdisplaywidth(line) > 56 then return end
          end
          state.header = output
          refresh()
        end))
    end
    set_quote(wrap_quote(quotes[os.time() % #quotes + 1]))
    if vim.fn.executable("fortune") == 1 then
      -- Only request a fortune when a dashboard is actually rendered, never for
      -- explicit file/directory arguments, piped input or ordinary headless use.
      pcall(vim.system, { "fortune", "-s" }, { text = true, timeout = 300 }, vim.schedule_wrap(function(result)
        local text = result.stdout or ""
        if result.code ~= 0 or #text > 4096 or vim.trim(text) == "" then return end
        local ok, rendered = pcall(wrap_quote, text)
        if not ok or not rendered then return end
        set_quote(rendered)
        refresh()
      end))
    end
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
