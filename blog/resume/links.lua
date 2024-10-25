function Link(el)
  -- This filter checks if the output format is LaTeX or PDF
  if quarto.doc.is_format("latex") then
    return pandoc.RawInline("latex", string.format("\\hreful{%s}{%s}", el.target, el.content[1].text))
  end
  return el
end

function Header(el)
  -- This filter should transform header content like
  -- ### content {organization="organization" title="title" start="start" stop="stop" }
  -- to
  -- ```### organization \textbar{} title \hfill dates``` in tex
  -- and
  -- ```### organization \textbar{} title\n**dates**``` in html
  for key, value in pairs(el.attr.attributes) do
    print("Custom attribute: ", key, " = ", value)
  end

  print(el.content)
  if quarto.doc.is_format("latex") then
    -- "%s \\textbar{} %s \\hfill %s - %s",
    local content = {
      el.attributes.title,
      pandoc.Space(),
      pandoc.RawInline("latex", "\\textbar{}"),
      pandoc.Space(),
      el.attributes.organization,
      pandoc.Space(),
      pandoc.RawInline("latex", "\\hfill"),
      pandoc.Space(),
      el.attributes.start,
      pandoc.Space(),
      pandoc.Str("-"),
      pandoc.Space(),
      el.attributes.stop,
    }
    print(content)

    if #el.content then
      table.insert(el.content, pandoc.Space())
      table.insert(el.content, pandoc.RawInline("latex", "\\textbar{}"))
      table.insert(el.content, pandoc.Space())

      -- NOTE: Do not use index assignment, it is broken.
      for index, item in ipairs(content) do
        table.insert(el.content, item)
      end
    else
      el.content = content
    end

    return el
  elseif quarto.doc.is_format("html") then
    local content = {
      el.attributes.title,
      pandoc.Space(),
      pandoc.RawInline("html", "|"),
      pandoc.Space(),
      el.attributes.organization,
    }

    if #el.content then
      table.insert(el.content, pandoc.Space())
      table.insert(el.content, pandoc.RawInline("html", "|"))
      table.insert(el.content, pandoc.Space())

      -- NOTE: Do not use index assignment, it is broken.
      for index, item in ipairs(content) do
        table.insert(el.content, item)
      end
    else
      el.content = content
    end

    return {
      el,
      pandoc.Strong(string.format("%s - %s", el.attributes.start, el.attributes.stop)),
    }
  end

  return el
end
