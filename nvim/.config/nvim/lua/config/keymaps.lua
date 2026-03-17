local map = vim.keymap.set
local default_opts = { silent = true, noremap = true }

-- Esc
map("i", "jj", "<Esc>", {})

-- Copy/Paste
map("v", "<leader>y", '"*y', default_opts)
map("n", "<leader>p", '"*p', default_opts)

-- Buffers
map("n", "<c-n>", "<cmd>bnext<CR>", default_opts)
map("n", "<c-p>", "<cmd>bprev<CR>", default_opts)
map("n", "<leader>b", ":b#|bd#<CR>", default_opts)

-- Windows
map("n", "<C-h>", "<C-w>h", default_opts)
map("n", "<C-j>", "<C-w>j", default_opts)
map("n", "<C-k>", "<C-w>k", default_opts)
map("n", "<C-l>", "<C-w>l", default_opts)
map("n", "<leader>q", ":q<CR>", default_opts)
map("n", "<leader>w", ":w<CR>", default_opts)

-- Save
vim.cmd("com! W w")
vim.cmd("com! Wq wq")
vim.cmd("com! WQ wq")

-- Sort
map("v", "<F9>", ":sort<CR>", default_opts)

------------------------------------------------

-- Command Line: Fuzzy search command history using Telescope
map("c", "<C-f>", function()
  require("telescope.builtin").command_history()
end, vim.tbl_extend("force", default_opts, { desc = "Search command history" }))

-- Telescope grep: two separate keymaps for with/without aider history
-- Regular grep EXCLUDING aider chat history (normal use) and other hidden files
map("n", "<leader>fg", function()
  require('telescope.builtin').live_grep({
    vimgrep_arguments = {
      "rg",
      "--color=never",
      "--no-heading",
      "--with-filename",
      "--line-number",
      "--column",
      "--smart-case",
      "--hidden",
      "--glob=!*.aider.chat.history.*",
      "--glob=!**/.aider/*"
    }
  })
end, vim.tbl_extend("force", default_opts, { desc = "Live grep (exclude hidden)" }))

-- Grep INCLUDING everything, including aider chat history and other hidden files (for debugging purposes)
map("n", "<leader>fG", function()
  require('telescope.builtin').live_grep()
end, vim.tbl_extend("force", default_opts, { desc = "Live grep (include all)" }))
