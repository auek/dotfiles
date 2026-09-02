return {
  "neanias/everforest-nvim",
  dependencies = { "ellisonleao/gruvbox.nvim" },
  version = false,
  lazy = false,
  priority = 1000,
  config = function()
    vim.opt.background = "dark"
    require("everforest").setup({
      background = "hard",
      transparent_background_level = 0,
      italics = false,
      disable_italic_comments = true,
    })

    require("gruvbox").setup({
      italic = {
        strings = false,
        comments = false,
        operators = false,
        folds = false,
      },
    })

    vim.g.dotfiles_theme = "everforest"
    vim.g.dotfiles_theme_background = "#272e33"

    local theme_file = vim.fn.expand("~/.local/state/dotfiles/theme/current/nvim.lua")
    local theme_signature = ""

    local apply_theme = function()
      local success, errmsg
      if vim.fn.filereadable(theme_file) == 1 then
        success, errmsg = pcall(dofile, theme_file)
      else
        vim.g.dotfiles_theme = "everforest"
        vim.g.dotfiles_theme_background = "#272e33"
        success, errmsg = pcall(vim.cmd.colorscheme, "everforest")
      end

      if not success then
        vim.notify("Error applying current colorscheme: " .. errmsg, vim.log.levels.ERROR)
      end
    end

    local signature = function()
      return vim.fn.resolve(theme_file) .. ":" .. vim.fn.getftime(theme_file)
    end

    apply_theme()
    theme_signature = signature()

    vim.api.nvim_create_user_command("ReloadTheme", apply_theme, {
      desc = "Reapply the selected dotfiles theme",
    })

    -- Reapply when theme-set swaps the runtime `current` symlink. The resolved
    -- path changes on a switch, and the mtime catches in-place edits; both are
    -- cheap to compare on focus/enter/idle.
    local watch = vim.api.nvim_create_augroup("DotfilesThemeReload", { clear = true })
    vim.api.nvim_create_autocmd({ "FocusGained", "BufEnter", "CursorHold" }, {
      group = watch,
      pattern = "*",
      callback = function()
        local current = signature()
        if current ~= theme_signature then
          theme_signature = current
          apply_theme()
        end
      end,
    })
  end
}
