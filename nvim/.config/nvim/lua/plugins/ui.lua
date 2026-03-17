return {
  {
    "nvim-tree/nvim-tree.lua",
    dependencies = { "kyazdani42/nvim-web-devicons" },
    opts = {
      filters = { dotfiles = true }
    },
    init = function()
      vim.g.loaded_netrw = 1
      vim.g.loaded_netrwPlugin = 1
    end,
    keys = {
      { "<leader>fe", "<cmd>NvimTreeFindFileToggle<CR>", mode = "n", desc = "Toggle NvimTree" }
    },
  },

  -- Status line
  {
    "nvim-lualine/lualine.nvim",
    dependencies = { "kyazdani42/nvim-web-devicons" },
    config = function()
      require("lualine").setup({
        options = { theme = "gruvbox" }
      })
    end,
  },


  -- Fuzzy finder
  {
    "nvim-telescope/telescope.nvim",
    version = "0.1.8",
    dependencies = {
      "nvim-lua/plenary.nvim",
      { 'nvim-telescope/telescope-fzf-native.nvim', build = 'make' },
    },
    init = function()
      local telescope = require("telescope")
      telescope.load_extension("notify")
      telescope.load_extension("fzf")
    end,
    opts = {
      defaults = {
        file_ignore_patterns = {
          "node_modules", "build", "dist", ".git", ".cache"
        },
      },
      pickers = {
        find_files = {
          hidden = true
        },
        live_grep = {
          additional_args = { "--hidden" }
        },
      },
      extensions = {
        fzf = {
          fuzzy = true,                   -- false will only do exact matching
          override_generic_sorter = true, -- override the generic sorter
          override_file_sorter = true,    -- override the file sorter
          case_mode = "smart_case",       -- or "ignore_case" or "respect_case"
        }
      },
    },
    keys = {
      { "<leader>ff", "<cmd>Telescope find_files<CR>", mode = "n", desc = "Find files" },
      {
        "<leader>fF",
        function()
          require("telescope.builtin").find_files({
            hidden = true,
            no_ignore = true,
          })
        end,
        mode = "n",
        desc = "Find all files"
      },
      {
        "<leader>fG",
        function()
          require("telescope.builtin").live_grep({
            additional_args = { "--hidden", "--no-ignore" }
          })
        end,
        mode = "n",
        desc = "Live grep (search everything)"
      },
      { "<leader>fo", "<cmd>Telescope oldfiles<CR>",   mode = "n", desc = "Old files" },
      { "<leader>fh", "<cmd>Telescope help_tags<CR>",  mode = "n", desc = "Help tags" },
      { "<leader>ls", "<cmd>Telescope buffers<CR>",    mode = "n", desc = "List buffers" },
      { "<leader>ma", "<cmd>Telescope marks<CR>",      mode = "n", desc = "List marks" },
    },
  },

  -- Start screen
  {
    "glepnir/dashboard-nvim",
    event = "VimEnter",
    dependencies = { "nvim-tree/nvim-web-devicons" },
    config = function()
      require("dashboard").setup({
        theme = 'doom',
        config = {
          header = {
            "                                                     ",
            "                                                     ",
            "                                                     ",
            "                                                     ",
            "                                                     ",
            "  ███╗   ██╗███████╗ ██████╗ ██╗   ██╗██╗███╗   ███╗ ",
            "  ████╗  ██║██╔════╝██╔═══██╗██║   ██║██║████╗ ████║ ",
            "  ██╔██╗ ██║█████╗  ██║   ██║██║   ██║██║██╔████╔██║ ",
            "  ██║╚██╗██║██╔══╝  ██║   ██║╚██╗ ██╔╝██║██║╚██╔╝██║ ",
            "  ██║ ╚████║███████╗╚██████╔╝ ╚████╔╝ ██║██║ ╚═╝ ██║ ",
            "  ╚═╝  ╚═══╝╚══════╝ ╚═════╝   ╚═══╝  ╚═╝╚═╝     ╚═╝ ",
            "                                                     ",
            "                                                     ",
            "                                                     ",
          },
          center = {
            {
              icon = "󰈞 ",
              icon_hl = "Title",
              desc = "Find File",
              desc_hl = "String",
              key = "f",
              keymap = "SPC f f",
              key_hl = "Number",
              action = "Telescope find_files"
            },
            {
              icon = "󰊄 ",
              icon_hl = "Title",
              desc = "Find Text",
              desc_hl = "String",
              key = "g",
              keymap = "SPC f g",
              key_hl = "Number",
              action = "Telescope live_grep"
            },
            {
              icon = "󰈚 ",
              icon_hl = "Title",
              desc = "Recent Files",
              desc_hl = "String",
              key = "r",
              keymap = "SPC f o",
              key_hl = "Number",
              action = "Telescope oldfiles"
            },
            {
              icon = "󰈔 ",
              icon_hl = "Title",
              desc = "New File",
              desc_hl = "String",
              key = "n",
              keymap = "SPC f n",
              key_hl = "Number",
              action = "DashboardNewFile"
            },
            {
              icon = "󰊅 ",
              icon_hl = "Title",
              desc = "Settings",
              desc_hl = "String",
              key = "s",
              keymap = "SPC f s",
              key_hl = "Number",
              action = "Telescope vim_options"
            },
          }
        }
      })
    end,
  },
  -- Key binding hints
  { "folke/which-key.nvim", config = true },

  -- Diagnostics window
  {
    "folke/trouble.nvim",
    dependencies = "kyazdani42/nvim-web-devicons",
    config = true,
  },

  -- Notifications
  {
    "rcarriga/nvim-notify",
    init = function()
      vim.notify = require("notify")
    end,
  },

  -- Markdown preview
  {
    "iamcco/markdown-preview.nvim",
    cmd = { "MarkdownPreviewToggle", "MarkdownPreview", "MarkdownPreviewStop" },
    build = "cd app && npm install",
    init = function()
      vim.g.mkdp_filetypes = { "markdown" }
    end,
    ft = { "markdown" },
  },
}
