return {
  -- Mason for LSP server installation
  {
    "williamboman/mason.nvim",
    cmd = "Mason",
    config = function()
      require("mason").setup()
    end,
  },

  -- Mason LSP Config for bridge between Mason and lspconfig
  {
    "williamboman/mason-lspconfig.nvim",
    dependencies = {
      "williamboman/mason.nvim",
      "neovim/nvim-lspconfig",
    },
    config = function()
      local lspconfig = require("lspconfig")
      local mason_lspconfig = require("mason-lspconfig")
      local capabilities = require("cmp_nvim_lsp").default_capabilities()

      mason_lspconfig.setup({
        ensure_installed = {
          "bashls",
          "ts_ls",
          "lua_ls",
          "eslint",
          "yamlls",
          "ansiblels",
          "astro",
          "pyright",
          "marksman",
        },
        handlers = {
          -- Default handler using new Nvim 0.11+ API
          function(server_name)
            vim.lsp.config(server_name, { capabilities = capabilities })
            vim.lsp.enable(server_name)
          end,
          -- Custom handler for lua_ls
          lua_ls = function()
            vim.lsp.config("lua_ls", {
              capabilities = capabilities,
              settings = {
                Lua = {
                  diagnostics = {
                    globals = { "vim" },
                  },
                },
              },
            })
            vim.lsp.enable("lua_ls")
          end,
          -- Custom handler for ansiblels
          ansiblels = function()
            vim.lsp.config("ansiblels", {
              capabilities = capabilities,
              settings = {
                ansible = {
                  validation = {
                    lint = {
                      enabled = true,
                      path = vim.fn.exepath("ansible-lint"),
                    },
                  },
                },
              },
            })
            vim.lsp.enable("ansiblels")
          end,
        },
      })
    end,
  },

  -- Main LSP configuration plugin
  {
    "neovim/nvim-lspconfig",
    cmd = { "LspInfo", "LspInstall", "LspStart", "LspStop", "LspRestart" },
    config = function()
      -- This empty config ensures the plugin's setup hook is run by lazy.nvim
      -- All server-specific setups are handled by mason-lspconfig's handlers.
    end,
    keys = {
      { "gd",         "<cmd>lua vim.lsp.buf.definition()<CR>",    mode = "n",          desc = "Go to definition" },
      { "gD",         "<cmd>lua vim.lsp.buf.declaration()<CR>",   mode = "n",          desc = "Go to declaration" },
      { "gh",         function() return vim.lsp.buf.hover() end,  desc = "Hover" },
      { "<leader>ca", vim.lsp.buf.code_action,                    mode = { "n", "v" }, desc = "Code Action" },
      { "<leader>cr", vim.lsp.buf.rename,                         desc = "Rename", },
      { "[d",         "<cmd>lua vim.diagnostic.goto_prev()<CR>",  mode = "n",          desc = "Previous diagnostic" },
      { "]d",         "<cmd>lua vim.diagnostic.goto_next()<CR>",  mode = "n",          desc = "Next diagnostic" },
      { "<leader>d",  "<cmd>lua vim.diagnostic.open_float()<CR>", mode = "n",          desc = "Open diagnostics" },
    }
  },
}
