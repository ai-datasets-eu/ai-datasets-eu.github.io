-- Builds the top of every survey page from its YAML header:
-- a source link, then a short fact table (who / when / where / sample / question).
-- Pages without a `who` field (the overview) are left untouched.

local function html(v)
  if v == nil or type(v) == "boolean" then return nil end
  local doc
  if pandoc.utils.type(v) == "Inlines" then
    doc = pandoc.Pandoc({ pandoc.Plain(v) })
  elseif pandoc.utils.type(v) == "Blocks" then
    doc = pandoc.Pandoc(v)
  else
    doc = pandoc.Pandoc({ pandoc.Plain({ pandoc.Str(pandoc.utils.stringify(v)) }) })
  end
  local out = pandoc.write(doc, "html"):gsub("^<p>", ""):gsub("</p>%s*$", "")
  if out == "" then return nil end
  return out
end

local pills = { workers = "pill-workers", firms = "pill-firms", individuals = "pill-individuals" }

function Pandoc(doc)
  local m = doc.meta
  if not m.who then return doc end

  local rows = {}
  local function row(label, value)
    if value and value ~= "" then
      rows[#rows + 1] = "<dt>" .. label .. "</dt><dd>" .. value .. "</dd>"
    end
  end

  row("Who", html(m.who))
  row("When", html(m.when))
  row("Where", html(m.where))

  if m.asked then
    local label = pandoc.utils.stringify(m.asked)
    local cls = pills[label:lower()] or "pill-both"
    local sample = '<span class="pill ' .. cls .. '">' .. label .. "</span>"
    if m.sample then sample = sample .. html(m.sample) end
    row("Sample", sample)
  end

  -- Work or private use: shown as a coloured label in front of the question
  local uses = {
    work = { "pill-use-work", "At work", "Use for work only" },
    private = { "pill-use-private", "Private life", "Use outside work only" },
    both = { "pill-use-both", "Work and private", "Asked separately" },
    any = { "pill-use-any", "Any purpose", "Work and private use not separated" },
    firm = { "pill-use-firm", "Firm", "Use by the firm, not by individual workers" },
  }
  local use = m.use and uses[pandoc.utils.stringify(m.use):lower()]
  if m.use and not use then error("unknown `use` value in " .. (PANDOC_STATE.input_files[1] or "?")) end
  if use then
    local text = '<span class="pill ' .. use[1] .. '">' .. use[2] .. "</span>"
    text = text .. (m["use-note"] and html(m["use-note"]) or use[3])
    row("AI use", text)
  end

  row("Question", html(m.question))

  -- Respondent characteristics: one collapsible list for workers or individuals, one for firms
  local function list(v)
    if not v then return nil end
    if pandoc.utils.type(v) ~= "List" then return html(v) end
    local items = {}
    for _, x in ipairs(v) do items[#items + 1] = html(x) end
    return table.concat(items, ", ")
  end
  local d = m.demographics
  if d then
    local groups = {}
    for _, g in ipairs({ { "workers", "Workers" }, { "individuals", "Individuals" }, { "firms", "Firms" } }) do
      local items = list(d[g[1]])
      if items then
        groups[#groups + 1] = '<details class="demo"><summary>' .. g[2] .. "</summary>" .. items .. "</details>"
      end
    end
    if #groups > 0 then row("Demographics", table.concat(groups, "")) end
  end

  -- Does the survey measure AI adoption by workers and/or by firms?
  local adoption = {}
  if m["adoption-individuals"] then adoption[#adoption + 1] = "Individuals: " .. pandoc.utils.stringify(m["adoption-individuals"]) .. "%" end
  if m["adoption-workers"] then
    local text = "Workers: " .. pandoc.utils.stringify(m["adoption-workers"]) .. "%"
    if m["adoption-base"] then text = text .. " (" .. html(m["adoption-base"]) .. ")" end
    adoption[#adoption + 1] = text
  end
  if m["adoption-firms"] then
    local text = "Firms: " .. pandoc.utils.stringify(m["adoption-firms"]) .. "%"
    if m["adoption-firms-base"] then text = text .. " (" .. html(m["adoption-firms-base"]) .. ")" end
    adoption[#adoption + 1] = text
  end
  if m["adoption-text"] then adoption = { html(m["adoption-text"]) } end
  row("Adoption", #adoption > 0 and table.concat(adoption, " &middot; ") or "No adoption question")

  local out = {}
  if m.link then
    local url = pandoc.utils.stringify(m.link)
    local text = m["link-text"] and html(m["link-text"]) or url
    out[#out + 1] = '<p class="survey-link"><a href="' .. url .. '" target="_blank" rel="noopener">' .. text .. "</a></p>"
  end
  out[#out + 1] = '<dl class="survey-card">\n' .. table.concat(rows, "\n") .. "\n</dl>"
  if m.aim then
    local aim = '<p class="survey-aim"><strong>Main aim.</strong> ' .. html(m.aim)
    if m["other-topics"] then
      aim = aim .. '<br><strong>Also covers.</strong> ' .. html(m["other-topics"])
    end
    out[#out + 1] = aim .. "</p>"
  end

  table.insert(doc.blocks, 1, pandoc.RawBlock("html", table.concat(out, "\n")))
  return doc
end
