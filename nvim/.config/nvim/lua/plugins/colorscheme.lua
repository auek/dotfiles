return {
  "neanias/everforest-nvim",
  version = false,
  lazy = false,
  priority = 1000,
  config = function()
    vim.opt.background = "dark"
    require("everforest").setup({
      background = "medium",
      transparent_background_level = 0,
      italics = false,
      disable_italic_comments = true,
    })

    local success, errmsg = pcall(function()
      vim.cmd([[colorscheme everforest]])
    end)
    if not success then
      vim.notify("Error applying Everforest colorscheme: " .. errmsg, vim.log.levels.ERROR)
    end
  end
}
