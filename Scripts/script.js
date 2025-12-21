// Set today's date as default
document.addEventListener("DOMContentLoaded", () => {
  const dateInput = document.getElementById("date")
  const today = new Date().toISOString().split("T")[0]
  dateInput.value = today
})

// Form submission handler
document.getElementById("transactionForm").addEventListener("submit", function (e) {
  e.preventDefault()

  const submitBtn = document.querySelector(".btn-submit")
  const formData = new FormData(this)

  // Add loading state
  submitBtn.classList.add("loading")
  submitBtn.disabled = true

  // Get form values
  const transactionData = {
    type: document.getElementById("transactionType").value,
    amount: Number.parseFloat(document.getElementById("amount").value),
    category: document.getElementById("category").value,
    description: document.getElementById("description").value,
    date: document.getElementById("date").value,
  }

  // Simulate API call
  setTimeout(() => {
    console.log("Transaction Data:", transactionData)

    // Show success message
    showSuccessMessage()

    // Reset form
    this.reset()
    document.getElementById("date").value = new Date().toISOString().split("T")[0]

    // Remove loading state
    submitBtn.classList.remove("loading")
    submitBtn.disabled = false

    // Remove validation classes
    this.classList.remove("was-validated")
  }, 1500)

  // Add validation classes
  this.classList.add("was-validated")
})

// Cancel button handler
function cancelTransaction() {
  const form = document.getElementById("transactionForm")

  // Show confirmation dialog
  if (confirm("Are you sure you want to cancel? All entered data will be lost.")) {
    form.reset()
    form.classList.remove("was-validated")

    // Reset date to today
    document.getElementById("date").value = new Date().toISOString().split("T")[0]

    // Optional: Navigate back or close modal
    console.log("Transaction cancelled")
  }
}

// Success message function
function showSuccessMessage() {
  // Create success alert
  const alert = document.createElement("div")
  alert.className = "alert alert-success alert-dismissible fade show position-fixed"
  alert.style.cssText = `
        top: 20px;
        right: 20px;
        z-index: 9999;
        min-width: 300px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        border: none;
        border-radius: 12px;
    `

  alert.innerHTML = `
        <i class="fas fa-check-circle me-2"></i>
        <strong>Success!</strong> Transaction added successfully.
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `

  document.body.appendChild(alert)

  // Auto remove after 3 seconds
  setTimeout(() => {
    if (alert.parentNode) {
      alert.remove()
    }
  }, 3000)
}

// Real-time form validation
document.querySelectorAll(".custom-input, .custom-select, .custom-textarea").forEach((input) => {
  input.addEventListener("blur", function () {
    if (this.checkValidity()) {
      this.classList.add("is-valid")
      this.classList.remove("is-invalid")
    } else {
      this.classList.add("is-invalid")
      this.classList.remove("is-valid")
    }
  })

  input.addEventListener("input", function () {
    this.classList.remove("is-valid", "is-invalid")
  })
})

// Amount input formatting
document.getElementById("amount").addEventListener("input", function () {
  const value = this.value
  if (value && !isNaN(value)) {
    // Ensure only 2 decimal places
    if (value.includes(".")) {
      const parts = value.split(".")
      if (parts[1] && parts[1].length > 2) {
        this.value = Number.parseFloat(value).toFixed(2)
      }
    }
  }
})

// Dynamic category icons based on transaction type
document.getElementById("transactionType").addEventListener("change", function () {
  const categorySelect = document.getElementById("category")
  const isIncome = this.value === "income"

  if (isIncome) {
    categorySelect.innerHTML = `
            <option value="">Select category</option>
            <option value="salary">💼 Salary</option>
            <option value="freelance">💻 Freelance</option>
            <option value="investment">📈 Investment</option>
            <option value="gift">🎁 Gift</option>
            <option value="other">📋 Other</option>
        `
  } else {
    categorySelect.innerHTML = `
            <option value="">Select category</option>
            <option value="food">🍽️ Food</option>
            <option value="rent">🏠 Rent</option>
            <option value="bills">⚡ Bills</option>
            <option value="shopping">🛍️ Shopping</option>
            <option value="other">📋 Other</option>
        `
  }
})
