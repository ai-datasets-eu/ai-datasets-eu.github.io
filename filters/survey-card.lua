-- Builds the fact tables of the site.
--
-- 1. Survey pages (surveys/<year>/*.qmd): the YAML header gives a source link, then a short
--    fact table (who / when / where / sample / AI use / question / demographics / adoption),
--    then the "Main aim" and "Also covers" lines. Pages without a `who` field are left alone.
-- 2. Country pages (countries/*.qmd): every national survey is a div
--      ::: {.survey-entry name="..." link="..." who="..." when="..." asked="Firms"
--           sample="..." use="firm" question="..."}
--      notes and chart
--      :::
--    which becomes a heading (linked to the source) with the same fact table above its content.
--    Attribute values may contain markdown.

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

-- Work or private use: shown as a coloured label (class, text)
local uses = {
  work = { "pill-use-work", "At work" },
  private = { "pill-use-private", "Private life" },
  any = { "pill-use-any", "Any purpose" },
  firm = { "pill-use-firm", "Firm" },
}

-- The rows shared by survey pages and country entries. `get(key)` returns the value of a field
-- (metadata or Inlines) or nil.
local function common_rows(get, row, where)
  row("Who", html(get("who")))
  row("When", html(get("when")))
  if where then row("Where", html(get("where"))) end

  local asked = get("asked")
  if asked then
    local label = pandoc.utils.stringify(asked)
    local cls = pills[label:lower()] or "pill-both"
    local sample = '<span class="pill ' .. cls .. '">' .. label .. "</span>"
    -- Number of respondents as a second pill: `n: "5,067"` gives "N = 5,067"; a value that does
    -- not start with a digit keeps its own sign, so `n: "≈ 7,500"` gives "N ≈ 7,500"
    local n = get("n")
    if n then
      local v = pandoc.utils.stringify(n)
      local text = v:match("^%d") and ("N = " .. v) or ("N " .. v)
      sample = sample .. '<span class="pill pill-n">' .. text .. "</span>"
    end
    if get("sample") then sample = sample .. html(get("sample")) end
    row("Sample", sample)
  end

  local u = get("use")
  local key = u and pandoc.utils.stringify(u):lower()
  local use = key and (key == "both" or uses[key])
  if u and not use then
    error("unknown `use` value '" .. pandoc.utils.stringify(u) .. "' in " .. (PANDOC_STATE.input_files[1] or "?"))
  end
  if use then
    -- The pill, then a `use-note` if any. `both` (work and private use asked separately) shows the
    -- two pills side by side; otherwise `use-label` can replace the pill text,
    -- e.g. "At work: respondent or colleagues"
    local function pill(p, text) return '<span class="pill ' .. p[1] .. '">' .. (text or p[2]) .. "</span>" end
    local text
    if key == "both" then
      text = pill(uses.work) .. pill(uses.private)
    else
      text = pill(use, get("use-label") and pandoc.utils.stringify(get("use-label")))
    end
    if get("use-note") then text = text .. html(get("use-note")) end
    row("AI use", text)
  end

  row("Question", html(get("question")))
end

local function new_rows()
  local rows = {}
  local function row(label, value)
    if value and value ~= "" then
      rows[#rows + 1] = "<dt>" .. label .. "</dt><dd>" .. value .. "</dd>"
    end
  end
  return rows, row
end

-- Country pages: one entry per national survey
function Div(div)
  if not div.classes:includes("survey-entry") then return nil end
  local a = div.attributes
  local function get(key)
    local v = a[key]
    if v == nil or v == "" then return nil end
    local blocks = pandoc.read(v, "markdown").blocks
    return blocks[1] and blocks[1].content or nil
  end
  if not a.name then error("survey-entry without a name in " .. (PANDOC_STATE.input_files[1] or "?")) end

  local rows, row = new_rows()
  common_rows(get, row, false)

  local title = get("name")
  if a.link then title = { pandoc.Link(title, a.link, "", { target = "_blank", rel = "noopener" }) } end
  local out = {
    pandoc.Header(3, title, pandoc.Attr("", { "entry-title" })),
    pandoc.RawBlock("html", '<dl class="survey-card entry-card">\n' .. table.concat(rows, "\n") .. "\n</dl>"),
  }
  for _, b in ipairs(div.content) do out[#out + 1] = b end
  return pandoc.Div(out, pandoc.Attr("", { "survey-entry-out" }))
end

function Pandoc(doc)
  local m = doc.meta

  if not m.who then return doc end

  local rows, row = new_rows()
  common_rows(function(k) return m[k] end, row, true)

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

  -- The page title links to the source; the link text becomes its tooltip
  if m.link then
    local url = pandoc.utils.stringify(m.link)
    local tip = m["link-text"] and pandoc.utils.stringify(m["link-text"]) or url
    m.title = pandoc.MetaInlines({ pandoc.Link(m.title, url, tip,
      pandoc.Attr("", { "title-source" }, { target = "_blank", rel = "noopener" })) })
    if not m.pagetitle then m.pagetitle = pandoc.utils.stringify(m.title) end
    doc.meta = m
  end

  local out = {}
  out[#out + 1] = '<dl class="survey-card">\n' .. table.concat(rows, "\n") .. "\n</dl>"

  -- Under the table, two buttons jump to the sections below: the survey's aim and other topics,
  -- and its results (the page body: charts and notes)
  local has_about = m.aim or m["other-topics"]
  local has_results = #doc.blocks > 0
  local cues = {}
  if has_about then cues[#cues + 1] = '<a class="survey-cue no-external" href="#about">Main aim and topics <span aria-hidden="true">&darr;</span></a>' end
  if has_results then cues[#cues + 1] = '<a class="survey-cue no-external" href="#results">See the results <span aria-hidden="true">&darr;</span></a>' end
  if #cues > 0 then out[#out + 1] = '<div class="survey-cues">' .. table.concat(cues, "") .. "</div>" end

  -- The source link, table and buttons fill the first screen (styles.css: .survey-top)
  local blocks = { pandoc.RawBlock("html", '<div class="survey-top">\n' .. table.concat(out, "\n") .. "\n</div>") }
  if has_about then
    blocks[#blocks + 1] = pandoc.Header(2, "About the survey", pandoc.Attr("about", { "survey-section" }))
    local about = {}
    if m.aim then about[#about + 1] = '<p class="survey-aim"><strong>Main aim.</strong> ' .. html(m.aim) .. "</p>" end
    if m["other-topics"] then
      about[#about + 1] = '<p class="survey-aim"><strong>Also covers.</strong> ' .. html(m["other-topics"]) .. "</p>"
    end
    blocks[#blocks + 1] = pandoc.RawBlock("html", table.concat(about, "\n"))
  end
  if has_results then
    blocks[#blocks + 1] = pandoc.Header(2, "Results", pandoc.Attr("results", { "survey-section" }))
  end
  for _, b in ipairs(doc.blocks) do blocks[#blocks + 1] = b end
  doc.blocks = blocks
  return doc
end
