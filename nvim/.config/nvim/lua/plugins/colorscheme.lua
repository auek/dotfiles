return {
  "ellisonleao/gruvbox.nvim",
  lazy = false,
  priority = 1000,
  config = function()
    require("gruvbox").setup({
      italic = {
        strings = false,
        comments = false,
        operators = false,
        folds = false,
      },
    })

    vim.opt.background = "dark"
    local success, errmsg = pcall(function()
      vim.cmd([[colorscheme gruvbox]])
    end)
    if not success then
      vim.notify("Error applying gruvbox colorscheme: " .. errmsg, vim.log.levels.ERROR)
    end
  end
}
