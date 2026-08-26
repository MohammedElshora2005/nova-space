// ===== Animate Numbers =====
function animateNumbers() {
  const numbers = document.querySelectorAll(
    ".stat-number[data-target], .achievement-number[data-target]",
  );

  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          const target = parseInt(entry.target.getAttribute("data-target"));
          let current = 0;
          const increment = Math.ceil(target / 60);

          const interval = setInterval(() => {
            current += increment;
            if (current >= target) {
              current = target;
              clearInterval(interval);
            }
            entry.target.textContent = current + "+";
          }, 25);
          observer.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.3 },
  );

  numbers.forEach((num) => observer.observe(num));
}
animateNumbers();

// ===== 3D Parallax Effect =====
document.addEventListener("mousemove", function (e) {
  const planet = document.querySelector(".planet");
  const ring = document.querySelector(".ring");
  const x = (e.clientX / window.innerWidth - 0.5) * 20;
  const y = (e.clientY / window.innerHeight - 0.5) * 20;

  if (planet) {
    planet.style.transform = `translate(-50%, -50%) rotateX(${y * 0.5}deg) rotateY(${x * 0.5}deg)`;
  }

  if (ring) {
    ring.style.transform = `translate(-50%, -50%) rotateX(${60 + y * 0.3}deg) rotateZ(${x * 0.3}deg)`;
  }
});

// ===== Floating Particles =====
function createParticles() {
  const container = document.getElementById("particles");
  if (!container) return;

  const colors = ["#00D4FF", "#7B2FFC", "#FF006E", "#FFD700", "#00FF87"];

  for (let i = 0; i < 30; i++) {
    const particle = document.createElement("div");
    particle.className = "particle";
    particle.style.left = Math.random() * 100 + "%";
    particle.style.width = Math.random() * 4 + 2 + "px";
    particle.style.height = particle.style.width;
    particle.style.background =
      colors[Math.floor(Math.random() * colors.length)];
    particle.style.animationDuration = Math.random() * 20 + 10 + "s";
    particle.style.animationDelay = Math.random() * 15 + "s";
    particle.style.opacity = Math.random() * 0.5 + 0.2;
    container.appendChild(particle);
  }
}
createParticles();

// ===== Hamburger Menu =====
document.querySelector(".hamburger").addEventListener("click", function () {
  this.classList.toggle("active");
  document.querySelector(".nav-links").classList.toggle("active");
});

document.querySelectorAll(".nav-links a").forEach((link) => {
  link.addEventListener("click", () => {
    document.querySelector(".hamburger").classList.remove("active");
    document.querySelector(".nav-links").classList.remove("active");
  });
});

// ===== Active Link =====
document.querySelectorAll(".nav-links a").forEach((link) => {
  link.addEventListener("click", function () {
    document
      .querySelectorAll(".nav-links a")
      .forEach((l) => l.classList.remove("active"));
    this.classList.add("active");
  });
});

// ===== Navbar Scroll Effect =====
window.addEventListener("scroll", function () {
  const navbar = document.querySelector(".navbar");
  if (window.scrollY > 100) {
    navbar.classList.add("scrolled");
  } else {
    navbar.classList.remove("scrolled");
  }
});

// ===== Reveal Animation =====
const observerOptions = {
  threshold: 0.1,
  rootMargin: "0px 0px -50px 0px",
};

const observer = new IntersectionObserver((entries) => {
  entries.forEach((entry) => {
    if (entry.isIntersecting) {
      entry.target.style.opacity = "1";
      entry.target.style.transform = "translateY(0)";
    }
  });
}, observerOptions);

document
  .querySelectorAll(".mission-card, .tech-item, .team-card, .achievement-item")
  .forEach((el) => {
    el.style.opacity = "0";
    el.style.transform = "translateY(30px)";
    el.style.transition = "all 0.8s cubic-bezier(0.25, 0.46, 0.45, 0.94)";
    observer.observe(el);
  });

// ===== Contact Form Handler with API =====
document
  .getElementById("contactForm")
  .addEventListener("submit", async function (e) {
    e.preventDefault();
    const button = this.querySelector('button[type="submit"]');
    const originalText = button.innerHTML;
    const formData = new FormData(this);

    // Collect data
    const data = {
      name: formData.get("name"),
      email: formData.get("email"),
      specialty: formData.get("specialty"),
      message: formData.get("message"),
    };

    // Show loading state
    button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Sending...';
    button.disabled = true;

    try {
      const response = await fetch("/api/subscribe", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(data),
      });

      const result = await response.json();

      if (result.success) {
        // Success
        button.innerHTML = '<i class="fas fa-check"></i> Successfully Sent!';
        button.style.background = "linear-gradient(135deg, #00FF87, #00D4FF)";

        showNotification(result.message, "success");

        setTimeout(() => {
          button.innerHTML = originalText;
          button.disabled = false;
          button.style.background = "";
          this.reset();
        }, 3000);
      } else {
        // Error
        showNotification(
          result.message || "An error occurred while sending",
          "error",
        );
        button.innerHTML = originalText;
        button.disabled = false;
      }
    } catch (error) {
      console.error("Error:", error);
      showNotification("Connection error. Please try again.", "error");
      button.innerHTML = originalText;
      button.disabled = false;
    }
  });

// ===== Notification Function =====
function showNotification(message, type = "info") {
  // Remove old alerts
  const oldAlerts = document.querySelectorAll(".alert");
  oldAlerts.forEach((alert) => alert.remove());

  const alert = document.createElement("div");
  alert.className = `alert alert-${type}`;
  alert.textContent = message;

  const form = document.querySelector(".contact-form");
  form.insertBefore(alert, form.firstChild);

  // Hide notification after 5 seconds
  setTimeout(() => {
    alert.style.opacity = "0";
    alert.style.transform = "translateY(-20px)";
    alert.style.transition = "all 0.5s ease";
    setTimeout(() => alert.remove(), 500);
  }, 5000);
}

// ===== Mission Card Hover Effect =====
document.querySelectorAll(".mission-card").forEach((card) => {
  card.addEventListener("mouseenter", function () {
    this.querySelector(".mission-number").style.opacity = "0.3";
  });
  card.addEventListener("mouseleave", function () {
    this.querySelector(".mission-number").style.opacity = "0.15";
  });
});

// ===== Scroll to Top Button =====
const scrollBtn = document.createElement("button");
scrollBtn.innerHTML = '<i class="fas fa-arrow-up"></i>';
scrollBtn.className = "scroll-top-btn";
document.body.appendChild(scrollBtn);

window.addEventListener("scroll", function () {
  if (window.scrollY > 500) {
    scrollBtn.classList.add("visible");
  } else {
    scrollBtn.classList.remove("visible");
  }
});

scrollBtn.addEventListener("click", function () {
  window.scrollTo({
    top: 0,
    behavior: "smooth",
  });
});

// ===== Smooth Scroll for Anchor Links =====
document.querySelectorAll('a[href^="#"]').forEach((anchor) => {
  anchor.addEventListener("click", function (e) {
    e.preventDefault();
    const target = document.querySelector(this.getAttribute("href"));
    if (target) {
      target.scrollIntoView({
        behavior: "smooth",
        block: "start",
      });
    }
  });
});

// ===== Console Message =====
console.log("🚀 Nova - Space Exploration");
console.log("✨ Successfully Loaded");
console.log("🌌 Explore the universe without limits");
