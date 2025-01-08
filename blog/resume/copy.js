function addCopyToContacts() {
  const contacts = document.getElementById("contacts")
  Array.from(contacts.getElementsByClassName("floaty-item-text")).map(item => {
    const value = item.innerText

    const button = document.createElement("i")
    button.title = "Copy to Clipboard"
    button.dataset.bsToggle = "tooltip"
    button.dataset.bsPlacement = "right"
    button.dataset.bsCustomClass = "floaty-tooltip"
    button.style.marginLeft = 'auto'

    button.classList.add("bi", "bi-clipboard", "contact-copy", "px-1")

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

    item.appendChild(button)
  })
}

addCopyToContacts()
