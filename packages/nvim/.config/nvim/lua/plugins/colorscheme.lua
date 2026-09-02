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

    local apply_theme = function()
      local theme_file = vim.fn.expand("~/.local/state/dotfiles/theme/current/nvim.lua")
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

    apply_theme()
    vim.api.nvim_create_user_command("ReloadTheme", apply_theme, {
      desc = "Reapply the selected dotfiles theme",
    })
  end
}
