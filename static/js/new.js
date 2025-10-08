// On button click, send the form data to the backend
$("#addButton").click(function () {
  const word = $("#word").val();
  const translation = $("#translation").val();

  $.post("/add_word", { word, translation })
    .done(function (response) {
      alert(response.message); // Show success message
    })
    .fail(function (response) {
      alert(response.responseJSON.message); // Show error message
    });
});
