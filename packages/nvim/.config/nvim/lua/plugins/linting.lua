return {
  "mfussenegger/nvim-lint",
  enabled = require("config.settings").features.eslint,
  event = { "BufReadPost", "BufNewFile" },
  config = function()
    local lint = require("lint")
    local tools = require("config.project_tools")
    local filetypes = { javascript = true, javascriptreact = true, typescript = true, typescriptreact = true }
    local function check(buffer)
      if not vim.api.nvim_buf_is_valid(buffer) or vim.bo[buffer].buftype ~= "" then return end
      local filename = vim.api.nvim_buf_get_name(buffer)
      local executable = filetypes[vim.bo[buffer].filetype] and tools.executable(filename, "eslint")
      if not executable then
        vim.diagnostic.reset(lint.get_namespace("eslint"), buffer)
        return
      end
      vim.api.nvim_buf_call(buffer, function()
        lint.try_lint("eslint", {
          cwd = tools.cwd(filename),
          wrap_linter = function(linter)
            -- Never use the upstream linter's PATH fallback. Capture stderr
            -- too so configuration/runtime failures remain visible.
            linter.cmd = executable
            linter.stream = "both"
            return linter
          end,
        })
      end)
    end
    local group = vim.api.nvim_create_augroup("DotfilesEslint", { clear = true })
    vim.api.nvim_create_autocmd({ "FileType", "BufWritePost" }, {
      group = group,
      callback = function(event) check(event.buf) end,
    })
    check(vim.api.nvim_get_current_buf())
  end,
}
