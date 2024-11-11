function Slidey(items, { size }) {
  if (!items || !items.length) throw Error("Missing required items.")
  size = size || "80vh"
  console.log(items)

  const state = { currentIndex: items.length - 1 }

  function getByIndex(index) {
    const currentContent = items[index]
    if (!currentContent) throw Error(`No content for index \`${index}\`.`)
    return currentContent
  }

  function showNext(incr) {
    incr = incr || 1
    let nextIndex = (state.currentIndex + incr) % items.length
    nextIndex = nextIndex < 0 ? items.length + nextIndex : nextIndex

    contentCurrent = getByIndex(state.currentIndex)
    contentNext = getByIndex(nextIndex)

    contentCurrent.style.display = "block"
    contentNext.style.display = "block"

    contentNext.style.transform = "translateX(0px)"
    setTimeout(() => {
      contentCurrent.style.transform = `translateX(${size})`
    }, 300);

    state.currentIndex = nextIndex
  }

  showNext()

  return { showNext, items }
}

