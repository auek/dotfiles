local M = {}

function M.new()
  local sorters = require("telescope.sorters")
  local fuzzy = sorters.get_fzy_sorter()
  local fzy = require("telescope.algos.fzy")
  local last_prompt, terms
  local function words(prompt)
    if prompt ~= last_prompt then
      last_prompt, terms = prompt, vim.split(prompt, "%s+", { trimempty = true })
    end
    return terms
  end

  return sorters.Sorter:new({
    discard = true,
    scoring_function = function(_, prompt, path)
      local total = 0
      -- Every word must match; spaces separate terms rather than path characters.
      for _, term in ipairs(words(prompt)) do
        local score = fuzzy:scoring_function(term, path)
        if score < 0 then return -1 end
        total = total + score
      end
      return total
    end,
    highlighter = function(_, prompt, display)
      local positions, seen = {}, {}
      for _, term in ipairs(words(prompt)) do
        if fzy.has_match(term, display) then
          for _, position in ipairs(fuzzy:highlighter(term, display)) do
            if not seen[position] then
              seen[position] = true
              positions[#positions + 1] = position
            end
          end
        end
      end
      table.sort(positions)
      return positions
    end,
  })
end

return M
