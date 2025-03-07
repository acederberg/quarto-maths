function addCopyToContacts() {
  const contacts = document.getElementById("contacts")
  Array.from(contacts.getElementsByClassName("floaty-item")).map(item => {


    const itemText = item.querySelector(".card-text")
    const value = itemText.innerText

    const button = document.createElement("i")
    button.title = "Copy to Clipboard"
    button.dataset.bsToggle = "tooltip"
    button.dataset.bsPlacement = "right"
    button.dataset.bsCustomClass = "floaty-tooltip"
    button.dataset.bsOffset = "[0,16]"
    button.style.marginLeft = 'auto'

    button.classList.add("bi", "bi-clipboard", "contact-copy", "px-1", "hidden")

    button.addEventListener("click", () => {
      navigator.permissions.query({ name: "clipboard-write" }).then(async (result) => {
        if (result.state === "granted" || result.state === "prompt") {
          try {
            await navigator.clipboard.writeText(value);
          } catch (err) {
            document.execCommand("copy", value)
            console.error('Failed to copy text: ', err);
          }
        }
      });
    })
    button.addEventListener("mouseover", () => { button.classList.add("text-blue") })
    button.addEventListener("mouseout", () => { button.classList.remove("text-blue") })
    item.addEventListener("mouseover", () => { button.classList.remove("hidden") })
    item.addEventListener("mouseout", () => { button.classList.add("hidden") })

    itemText.appendChild(button)
  })
}

addCopyToContacts()
