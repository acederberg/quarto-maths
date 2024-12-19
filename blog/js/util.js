function FullPage() {
  document.getElementById("title-block-header").remove()
  document.getElementById("quarto-document-content").classList.add("px-1")
  const quartoContent = document.getElementById("quarto-content")
  quartoContent.classList.remove("page-columns")
}


