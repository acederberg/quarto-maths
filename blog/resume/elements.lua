function Link(el)
  -- This filter checks if the output format is LaTeX or PDF
  if quarto.doc.is_format("latex") then
    return pandoc.RawInline("latex", string.format("\\hreful{%s}{%s}", el.target, el.content[1].text))
  end
  return el
end

-- function BulletList(el)
--   if quarto.doc.is_format("latex") then
--     pandoc.template.apply(
--       "tightlist", el
--     )
--   end
-- end
