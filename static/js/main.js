// Mobile Hamburger Menu Navigation Toggle
document.addEventListener("DOMContentLoaded", () => {
    const mobileMenuButton = document.getElementById("mobileMenuButton");
    const mobileMenu = document.getElementById("mobileMenu");
    const hamburgerIcon = document.getElementById("hamburgerIcon");

    if (mobileMenuButton && mobileMenu) {
        mobileMenuButton.addEventListener("click", () => {
            const isHidden = mobileMenu.classList.contains("hidden");
            if (isHidden) {
                mobileMenu.classList.remove("hidden");
                if (hamburgerIcon) {
                    hamburgerIcon.classList.remove("fa-bars");
                    hamburgerIcon.classList.add("fa-xmark");
                }
            } else {
                mobileMenu.classList.add("hidden");
                if (hamburgerIcon) {
                    hamburgerIcon.classList.remove("fa-xmark");
                    hamburgerIcon.classList.add("fa-bars");
                }
            }
        });
    }
});
