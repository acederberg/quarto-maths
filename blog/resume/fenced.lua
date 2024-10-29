-------------------------------------------------------------------------------
-- Helpers

local function has_key(t, value)
  for k, v in pairs(t) do
    if v == value then
      return true
    end
  end

  return false
end

local function merge(a, b)
  local merged = {}

  for k, v in pairs(a) do
    merged[k] = v
  end

  local n = #a

  for j, w in pairs(b) do
    merged[j + n] = w
  end

  return merged
end

local function printTable(v, level)
  level = level or 0
  if level == 0 then
    print("---")
  end

  for key, value in pairs(v) do
    if type(value) == "table" then
      printTable(value, level + 1)
    else
      print(string.rep(" ", level * 2), key, value)
    end
  end

  if level == 0 then
    print("---")
  end
end

local function it_works()
  return pandoc.Strong({ pandoc.Str("It"), pandoc.Space(), pandoc.Str("works!") })
end

-------------------------------------------------------------------------------

local resume_metadata = {}

-- Populate metadata into global ``resume_metadata``.
--
-- NOTE: Defining locals like this is, in my opinion, a disgusting pattern.
--       However this pattern is supported by
--       https://pandoc.org/lua-filters.html#replacing-placeholders-with-their-metadata-value
--
local function populate_resume_metadata(meta)
  resume_metadata.skills = meta.resume.skills
  resume_metadata.sidebar = meta.resume.sidebar
  resume_metadata.experience = meta.resume.body.experience
end

-- This filter should transform header content like
-- ### content {organization="organization" title="title" start="start" stop="stop" }
-- to
--
-- ```### organization \textbar{} title \hfill dates``` in tex
--
-- and
--
-- ```### organization \textbar{} title\n**dates**``` in html
--
local function create_experience_header(data)
  if quarto.doc.is_format("latex") then
    local textbar = { pandoc.Space(), pandoc.RawInline("latex", "\\textbar{}"), pandoc.Space() }
    local spacer = {
      pandoc.Space(),
      pandoc.RawInline("latex", "\\hfill"),
      pandoc.Space(),
    }

    local content = merge({}, data.title)
    content = merge(content, textbar)
    content = merge(content, data.organization)
    content = merge(content, spacer)
    content = merge(content, data.start)
    content = merge(content, {
      pandoc.Space(),
      pandoc.Str("-"),
      pandoc.Space(),
    })
    content = merge(content, data.stop)

    return pandoc.Header(3, content)
  elseif quarto.doc.is_format("html") then
    local content = merge({}, data.title)
    content = merge(content, {
      pandoc.Space(),
      pandoc.RawInline("html", "|"),
      pandoc.Space(),
    })
    content = merge(content, data.organization)
    local header = pandoc.Header(3, content)

    content = merge({}, data.start)
    content = merge(content, {
      pandoc.Space(),
      pandoc.Str("-"),
      pandoc.Space(),
    })
    local strong = pandoc.Strong(merge(content, data.stop))

    return {
      header,
      strong,
    }
  end

  return pandoc.Header(3, "Unsupported Format!")
end

local function create_experience_item(el)
  local name = el.attributes.experience_item
  local data = resume_metadata.experience[name]
  local content = { create_experience_header(data) }

  content = merge(content, el.content)
  el.content = content
  return el
end

local function create_experience(el)
  local content = {
    pandoc.Header(2, "Experience"),
  }
  content = merge(content, el.content)
  return content
end

-------------------------------------------------------------------------------
--- Skills fence
---

local function create_skills_item(data)
  local content = { pandoc.Strong(":"), pandoc.Space() }
  if quarto.doc.is_format("html") then
    content = merge(data.icon, content)
  end
  content = merge(data.name, content)
  -- end
  -- content = merge(pandoc.Image
  content = merge(content, data.experience)
  return pandoc.Para(content)
end

local function create_skills(el)
  local content = {
    pandoc.Header(2, { pandoc.Str("Skills") }),
  }
  content = merge(content, el.content)

  printTable(resume_metadata.sidebar.skills)

  local skill_data
  local content_list = {}
  print("==============================")
  printTable(resume_metadata.skills)
  print("==============================")
  for skill_index, skill_name in pairs(resume_metadata.sidebar.skills) do
    print(skill_name[1])
    printTable(resume_metadata.skills[skill_name[1]])
    -- skill_data = resume_metadata.skills[skill_name]
    -- content_list = merge(content_list, { create_skills_item(skill_data) })
  end

  local listing = { pandoc.BulletList(content_list) }
  content = merge(content, el.content)
  el.content = merge(content, listing)

  return el
end

-------------------------------------------------------------------------------
--- Contacts fence.

local function create_contacts_html_item(data)
  local content = merge(data.icon, { pandoc.Space() })
  content = merge(content, data.value)
  printTable(content)

  return pandoc.Para(content)
end

local function create_contacts_html(el)
  local content = { pandoc.Header(2, "Contacts") }

  local content_list = {}

  for contact_field, contact_data in pairs(resume_metadata.sidebar.contact) do
    content_list = merge(content_list, { create_contacts_html_item(contact_data) })
  end

  local listing = { pandoc.BulletList(content_list) }

  content = merge(content, el.content)
  el.content = merge(content, listing)
  return el
end

local function create_contacts_tex(el)
  el.content = it_works()
  return el
end

local function create_contacts(el)
  if quarto.doc.is_format("latex") then
    return create_contacts_tex(el)
  elseif quarto.doc.is_format("html") then
    return create_contacts_html(el)
  else
    return pandoc.Null()
  end
end

-------------------------------------------------------------------------------

local function hydrate_fenced(el)
  local identifier = el.attr.identifier
  if identifier == "skills" then
    print("Found Skills!")
    return create_skills(el)
  elseif identifier == "contacts" then
    print("Found Contacts!")
    return create_contacts(el)
  elseif identifier == "experience" then
    print("Found Experience!")
    return create_experience(el)
  elseif has_key(el.attr.classes, "experience") then
    print("Found ExperienceItem!")
    return create_experience_item(el)
  end

  return el
end

return {
  { Meta = populate_resume_metadata },
  { Div = hydrate_fenced },
}
