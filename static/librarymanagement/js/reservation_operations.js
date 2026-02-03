/**
 * Reservation Operations Module
 * Functions for managing book reservations
 */

/**
 * Mark reservation as ready for pickup
 * @param {string|number} reservationId - The reservation ID
 */
function markReady(reservationId) {
  Swal.fire({
    title: "Mark as Ready?",
    text: "This will notify the user that their book is ready for pickup.",
    icon: "question",
    showCancelButton: true,
    confirmButtonText: "Yes, mark as ready",
    confirmButtonColor: "#10b981",
  }).then((result) => {
    if (result.isConfirmed) {
      fetchWithCsrf(`/library/reservations/${reservationId}/ready/`, {
        notify: "true",
      }).then((response) =>
        handleApiResponse(response, "Reservation marked as ready.", true),
      );
    }
  });
}

/**
 * Notify user about their reservation
 * @param {string|number} reservationId - The reservation ID
 */
function notifyUser(reservationId) {
  Swal.fire({
    title: "Notify User?",
    text: "Send a notification to the user about their reservation.",
    icon: "question",
    showCancelButton: true,
    confirmButtonText: "Yes, send notification",
    confirmButtonColor: "#3b82f6",
  }).then((result) => {
    if (result.isConfirmed) {
      fetchWithCsrf(`/library/reservations/${reservationId}/notify/`, {}).then(
        (response) =>
          handleApiResponse(response, "User has been notified.", true),
      );
    }
  });
}

/**
 * Fulfill a reservation (mark as completed)
 * @param {string|number} reservationId - The reservation ID
 */
function fulfillReservation(reservationId) {
  Swal.fire({
    title: "Fulfill Reservation?",
    text: "Mark this reservation as fulfilled and proceed with checkout.",
    icon: "question",
    showCancelButton: true,
    confirmButtonText: "Yes, fulfill it",
    confirmButtonColor: "#10b981",
  }).then((result) => {
    if (result.isConfirmed) {
      fetchWithCsrf(`/library/reservations/${reservationId}/fulfill/`, {}).then(
        (response) =>
          handleApiResponse(response, "Reservation has been fulfilled.", true),
      );
    }
  });
}

/**
 * Cancel a reservation
 * @param {string|number} reservationId - The reservation ID
 */
function cancelReservation(reservationId) {
  Swal.fire({
    title: "Cancel Reservation?",
    text: "This action cannot be undone.",
    icon: "warning",
    showCancelButton: true,
    confirmButtonText: "Yes, cancel it",
    confirmButtonColor: "#ef4444",
    input: "textarea",
    inputPlaceholder: "Reason for cancellation (optional)",
  }).then((result) => {
    if (result.isConfirmed) {
      fetchWithCsrf(`/library/reservations/${reservationId}/cancel/`, {
        reason: result.value || "",
      }).then((response) =>
        handleApiResponse(response, "Reservation has been cancelled.", true),
      );
    }
  });
}
