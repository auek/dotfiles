return {
  {
    "christoomey/vim-tmux-navigator",
    cmd = {
      "TmuxNavigateLeft",
      "TmuxNavigateDown",
      "TmuxNavigateUp",
      "TmuxNavigateRight",
      "TmuxNavigatePrevious",
    },
    keys = {
      { "<c-h>", "<cmd><C-U>TmuxNavigateLeft<cr>" },
      { "<c-j>", "<cmd><C-U>TmuxNavigateDown<cr>" },
      { "<c-k>", "<cmd><C-U>TmuxNavigateUp<cr>" },
      { "<c-l>", "<cmd><C-U>TmuxNavigateRight<cr>" },
      { "<c-\\>", "<cmd><C-U>TmuxNavigatePrevious<cr>" },
    },
  },
  -- GitHub Copilot
  -- {
  --   "github/copilot.vim",
  --   lazy = false,
  --   keys = {
  --     { "<C-J>", "copilot#Accept(\"\\<CR>\")", expr = true, replace_keycodes = false,            mode = "i", desc = "Accept Copilot suggestion" },
  --     { "<M-]>", "<Plug>(copilot-next)",       mode = "i",  desc = "Next Copilot suggestion" },
  --     { "<M-[>", "<Plug>(copilot-previous)",   mode = "i",  desc = "Previous Copilot suggestion" },
  --   },
  --   init = function()
  --     vim.g.copilot_no_tab_map = true
  --   end,
  -- },
  {
    "Exafunction/windsurf.vim",
    config = function()
      -- disable by filetype
      vim.g.codeium_filetypes = {
        env = false,
      }
      -- disable by filename pattern (for secrets files)
      vim.api.nvim_create_autocmd("BufEnter", {
        pattern = { ".env", ".env.*", ".secrets", "*secret*", "*credential*", "*.pem", "*.key" },
        callback = function() vim.cmd("CodeiumDisable") end,
      })
      vim.api.nvim_create_autocmd("BufLeave", {
        pattern = { ".env", ".env.*", ".secrets", "*secret*", "*credential*", "*.pem", "*.key" },
        callback = function() vim.cmd("CodeiumEnable") end,
      })
      vim.keymap.set("i", "<C-J>", function()
        return vim.fn["codeium#Accept"]()
      end, { expr = true, silent = true })
    end,
  },
  -- Comment.nvim
  {
    'numToStr/Comment.nvim',
    dependencies = {
      {
        'JoosepAlviste/nvim-ts-context-commentstring',
        opts = {
          enable_autocmd = false,
        },
      },
    },
    opts = function()
      local pre_hook = require('ts_context_commentstring.integrations.comment_nvim').create_pre_hook()
      return {
        pre_hook = function(ctx)
          local ok, result = pcall(pre_hook, ctx)
          if ok and result then return result end
          return vim.bo.commentstring
        end,
      }
    end,
  },
}
