local defaults = {
  servers = { ts_ls = true, cssls = true, yamlls = true, bashls = true },
  parsers = { "bash", "css", "javascript", "json", "lua", "tsx", "typescript", "yaml" },
  server_options = {},
  format_timeout_ms = 3000,
  features = { format_on_save = false, eslint = false, markdown_preview = false },
}

-- This is trusted machine-local code, not a project-discovered configuration.
-- Lists replace defaults; server/feature maps merge so individual entries can
-- be added or disabled without duplicating the baseline.
local path = vim.fn.stdpath("config") .. "/local.lua"
if vim.fn.filereadable(path) == 1 then
  local ok, result = pcall(function()
    local value = dofile(path)
    assert(type(value) == "table", "expected a table")
    for key in pairs(value) do assert(defaults[key] ~= nil, "unknown setting: " .. tostring(key)) end
    local timeout = value.format_timeout_ms
    assert(timeout == nil or (type(timeout) == "number" and timeout % 1 == 0 and timeout > 0 and timeout <= 60000),
      "format_timeout_ms must be an integer between 1 and 60000")
    for name, enabled in pairs(value.servers or {}) do
      assert(type(name) == "string" and name:match("^[%w_]+$") and type(enabled) == "boolean",
        "servers must map LSP names to booleans")
    end
    if value.parsers then
      assert(vim.islist(value.parsers), "parsers must be a list")
      for _, name in ipairs(value.parsers) do
        assert(type(name) == "string" and name:match("^[%w_-]+$"), "invalid parser name")
      end
    end
    for name, enabled in pairs(value.features or {}) do
      assert(defaults.features[name] ~= nil and type(enabled) == "boolean", "invalid feature: " .. tostring(name))
    end
    assert(type(value.server_options or {}) == "table", "server_options must be a table")
    for name, options in pairs(value.server_options or {}) do
      assert(type(name) == "string" and type(options) == "table", "invalid server_options entry")
    end
    local settings = vim.tbl_deep_extend("force", defaults, value)
    settings.parsers = value.parsers or defaults.parsers
    return settings
  end)
  if ok then return result end
  vim.notify("Ignoring invalid " .. path .. ": " .. tostring(result), vim.log.levels.WARN)
end
return defaults
