local M = {}

function M.setup()
  require("everforest").setup({
    background = "hard",
    transparent_background_level = 0,
    italics = false,
    disable_italic_comments = true,
  })
  require("gruvbox").setup({
    italic = { strings = false, comments = false, operators = false, folds = false },
  })

  -- Same runtime selection as theme-set; no dependency on the home nvim package.
  local path = vim.fn.expand("~/.local/state/dotfiles/theme/current/nvim.lua")
  local function default_theme()
    vim.g.dotfiles_theme = "everforest"
    vim.g.dotfiles_theme_background = "#272e33"
    vim.opt.background = "dark"
    vim.cmd.colorscheme("everforest")
  end
  local function apply()
    default_theme()
    if vim.fn.filereadable(path) == 1 then
      local ok, err = pcall(dofile, path)
      if not ok then
        default_theme()
        vim.notify("Could not apply selected work theme: " .. tostring(err), vim.log.levels.WARN)
      end
    end
  end
  local function signature()
    return vim.fn.resolve(path) .. ":" .. vim.fn.getftime(path) .. ":" .. vim.fn.getfsize(path)
  end
  apply()
  local last = signature()
  vim.api.nvim_create_user_command("ReloadTheme", function()
    apply()
    last = signature()
  end, { desc = "Reload the theme-set selection" })
  local group = vim.api.nvim_create_augroup("NvimWorkThemeReload", { clear = true })
  vim.api.nvim_create_autocmd({ "FocusGained", "BufEnter", "CursorHold" }, {
    group = group,
    callback = function()
      local current = signature()
      if current ~= last then
        last = current
        apply()
      end
    end,
  })
end

return M
