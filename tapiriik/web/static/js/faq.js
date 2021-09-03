// This just handle the Q&A accordions stretch and retract on click
for (const el of document.getElementsByClassName("faq-topic-header")) {
    el.addEventListener("click", function (e) {
        this.parentElement.classList.toggle("active");
    });
}