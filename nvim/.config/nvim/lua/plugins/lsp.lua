return {
  -- Mason for LSP server installation
  {
    "mason-org/mason.nvim",
    opts = {},
  },

  -- Mason LSP Config for bridge between Mason and lspconfig
  {
    "mason-org/mason-lspconfig.nvim",
    dependencies = {
      "mason-org/mason.nvim",
      "neovim/nvim-lspconfig",
      "hrsh7th/cmp-nvim-lsp",
    },
    opts = {
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
    },
    config = function(_, opts)
      vim.lsp.config("*", {
        capabilities = require("cmp_nvim_lsp").default_capabilities(),
      })
      vim.lsp.config("lua_ls", {
        settings = {
          Lua = {
            diagnostics = {
              globals = { "vim" },
            },
          },
        },
      })

      require("mason-lspconfig").setup(opts)
    end,
  },

  -- Main LSP configuration plugin
  {
    "neovim/nvim-lspconfig",
    cmd = { "LspInfo", "LspInstall", "LspStart", "LspStop", "LspRestart" },
    keys = {
      { "gd",         "<cmd>lua vim.lsp.buf.definition()<CR>",    mode = "n",          desc = "Go to definition" },
      { "gD",         "<cmd>lua vim.lsp.buf.declaration()<CR>",   mode = "n",          desc = "Go to declaration" },
      { "gh",         function() return vim.lsp.buf.hover() end,  desc = "Hover" },
      { "<leader>ca", vim.lsp.buf.code_action,                    mode = { "n", "v" }, desc = "Code Action" },
      { "<leader>cr", vim.lsp.buf.rename,                         desc = "Rename", },
      { "[d",         function() vim.diagnostic.jump({ count = -1, float = true }) end, mode = "n", desc = "Previous diagnostic" },
      { "]d",         function() vim.diagnostic.jump({ count = 1, float = true }) end,  mode = "n", desc = "Next diagnostic" },
      { "<leader>d",  "<cmd>lua vim.diagnostic.open_float()<CR>", mode = "n",          desc = "Open diagnostics" },
    }
  },
}
