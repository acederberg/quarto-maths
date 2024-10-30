function Div(el)
  if el.attr.identifier == "example" then
    el.content = {
      pandoc.Header(2, "Test"),
      pandoc.Para("I Would Like an Icon Below"),
      pandoc.Para({
        pandoc.Str("{{<"),
        pandoc.Space(),
        pandoc.Str("iconify"),
        pandoc.Space(),
        pandoc.Str("devicon"),
        pandoc.Space(),
        pandoc.Str("python"),
        pandoc.Space(),
        pandoc.Str(">}}"),
      }),
    }
  end
  return el
end

function Para(el)
  print(el)
end
