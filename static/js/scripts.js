/**
 * The tagNum variable counts the number of tags in an entry
 * This is used to give an ID number to dynamically generated tags.
 * */
let tagNum = $(".view-tag").length + 1;

/**
 * This function takes the id of a tag, and extracts the number at the end
 *
 * @param {number} id The id of tag
 */
function getNumberFromId(id) {
    return id.match(/\d+/g)[0];
}

/**
 * The following code shows and hides the fields to update account information
 * on the user's Profile page. It changes the appearance and content of the buttons
 * used to toggle these fields.
 * It also alters the "aria-expanded" and "aria-hidden" properties for
 * accessibility purposes.
 *
 * @param {string} field The jQuery selector of the field to toggle
 */
function toggleField(field) {
    $(field).toggle();
    $(field).attr("aria-expanded", function (i, attr) {
        return attr === "true" ? "false" : "true";
    });
    $(field).attr("aria-hidden", function (i, attr) {
        return attr === "true" ? "false" : "true";
    });
    $(this).toggleClass("selected");
    $(this).find(".icon").text() === "edit"
        ? $(this).find(".icon").text("close")
        : $(this).find(".icon").text("edit");
}

/**
 * This function adds the tag created by the user to a hidden input field, separated by
 * comma.
 * If no content is present in the field, it simply adds the content of the new tag.
 * The hidden field will thus contain a list of all tags for the entry, separated
 * by commas.
 *
 * @param {string} inputEl The jQuery selector for the new tag input generated by the user
 */
function addToHiddenInput(inputEl) {
    if ($("#hidden_tags").val() != "") {
        return $("#hidden_tags").val() + "," + $(inputEl).val();
    } else {
        return $(inputEl).val();
    }
}

/**
 * This function expands textarea input fields to fit their content content automatically.
 * It is inspired inspired by Vanderson https://codepen.io/Vanderson
 */
function expandTextArea() {
    this.style.removeProperty("height");
    this.style.height = this.scrollHeight + 2 + "px";
}

/**
 * The following function generates the code for a new tag on an entry page.
 *
 * @param {string} id The id of the newly created tag
 * @param {string} word The content of the newly created tag
 */
function createTag(id, word) {
    return `<span id="${id}"class="view-tag badge badge-pill badge-primary tag"><a href="/listing/${word}">${word}</a></span>`;
}

/**
 * This function generates the code to create a new "delete tag" on an entry page.
 * Delete tags are displayed when the user is editing the tags, and allow for the deletion
 * of the corresponding tag.
 *
 * @param {string} id The id of the newly created delete tag
 * @param {string} word The content of the newly created delete tag
 */
function createDeleteTag(id, word) {
    return `<span id="${id}" class="badge badge-pill badge-primary tag delete-tag">${word}
    <span class="material-icons">cancel</span></span>`;
}

/**
 * This function deletes a tag when its corresponding "delete tag" is clicked.
 * It finds the id of its corresponding tag by using getNumberFromId, and removes
 * both the tags and it's delete tag counterpart from the DOM.
 * It also gets the string of tags in the #hidden_tags field, makes it an array to
 * remove the deleted tag from it, and rebuilds the string of tags separated by commas.
 */
function deleteTag() {
    $(this).click(function () {
        let viewId = "#tag" + getNumberFromId($(this).attr("id"));
        // Make value of hidden field an array, remove the deleted tag, then rebuild string
        let tagArray = $("#hidden_tags").val().split(",");
        let newTagArray = tagArray.filter((tag) => tag !== $(viewId).text());
        $("#hidden_tags").val(newTagArray.join());
        $(this).remove();
        $(viewId).remove();
    });
}

// Add a new tag to list and focus on it to edit
/**
 * This function creates a new tag and its corresponding delete tag.
 * It also creates a corresponding width machine, which is a span containing the content
 * of the new tag, used solely for the purpose of defining the width of the tag as the
 * input is being typed into.
 *
 * It also puts the browser's focus onto the newly created tag input.
 *
 * Finally it increments tagNum.
 */
function addNewTag() {
    let editTagId = "edit-tag-" + tagNum;
    let viewTagId = "tag" + tagNum;
    let widthMachineId = "width" + tagNum;
    let newEditTag = `<input id="${editTagId}" type="text" maxlength="20" placeholder="new tag" spellcheck="false" class="tag badge-pill badge-primary badge-input" />`;
    let newTag = createTag(viewTagId, "tag name");
    let newWidthMachine = `<span aria-hidden="true" id="${widthMachineId}"class="badge badge-pill badge-primary tag width-machine">invisible</span>`;
    $(this).before(newEditTag);
    $("#" + editTagId).focus();
    $("#view-tags").append(newTag);
    $(".entry").append(newWidthMachine);
    tagNum += 1;
}

/**
 * The textarea fields that have the data-expandable attribute are able to expand to fit their
 * content when keys are pressed or the input is clicked into.
 */
$("body")
    .on("keydown input", "textarea[data-expandable]", expandTextArea)
    .on("mousedown", "textarea[data-expandable]", expandTextArea);

// Copy content of new tag to tag list when created
$("body").on("keydown input", ".badge-input", function () {
    let viewId = "#tag" + getNumberFromId($(this).attr("id"));
    let widthId = "#width" + getNumberFromId($(this).attr("id"));
    // Update name of View Tag
    $(viewId + " a").text($(this).val());
    // Update tag url
    $(viewId + " a").attr("href", "../listing/" + $(this).val());
    $(widthId).text($(this).val());
    $(this).width($(widthId).width());
});

// Prevents line breaks in Review Name and tags.
// Pressing enter will instead send focus to the next element.
$("body").on("keypress", "#name, .badge-input", function (event) {
    if (event.keyCode === 13) {
        $(this).blur();
        return false;
    }
});

// Expandable text areas resize when window size is changed
$(window).resize(function () {
    $("textarea[data-expandable]").each(expandTextArea);
});

// Turning on Tag Edit mode
$("#edit-tags-btn").on("click", function () {
    $("#edit-tags").toggle();
    $("#view-tags-container").toggle();
});

// Saving changes to tags
$(document).on("click", "#save-tag-btn", function () {
    $("#edit-tags").toggle();
    $(".badge-input").each(function () {
        // If nothing has been inputed the new tag is deleted
        if (!$(this).val()) {
            $(this).remove();
            $("#tag" + getNumberFromId($(this).attr("id"))).remove();
        } else {
            let newTagContent = addToHiddenInput(this);
            let newDeleteTag = createDeleteTag(
                $(this).attr("id"),
                $(this).val()
            );
            $("#hidden_tags").val(newTagContent);
            $("#new-tag").before(newDeleteTag);
            $(".delete-tag").each(deleteTag);
            $(this).remove();
        }
    });
    // Send new tag information to the database
    sendTagData();
    // Remove element used to resize tag inputs
    $(".width-machine").each(function () {
        $(this).remove();
    });
    // Return to normal tag view
    $("#view-tags-container").toggle();
});

// In new entry form, changes text input text when a new file is chosen
$(".custom-file-input").change((e) => {
    let fileName = e.target.files[0].name;
    $(".custom-file-label").text(fileName);
});

// Only allow certain keystrokes in tag input fields
// Whether in entry or new entry page
// Inspired by https://stackoverflow.com/questions/43799032/allow-only-alphanumeric-in-textbox-using-jquery
$(document).on("keydown", ".badge-input", (e) => {
    let k = e.keyCode || e.which;
    let ok =
        (k >= 65 && k <= 90) || // A-Z
        (k >= 96 && k <= 105) || // a-z
        (k >= 35 && k <= 40) || // arrows
        k === 46 || //del
        k === 13 || //enter
        k === 8 || // backspaces
        k === 32 || // space
        (!e.shiftKey && k >= 48 && k <= 57); // only 0-9 (ignore SHIFT options)
    if (!ok || (e.ctrlKey && e.altKey)) {
        e.preventDefault();
    }
});

// Text is added to hidden tags field when tag input is unfocused
$(document).on("blur", "#new-entry .badge-input", function () {
    let newTags = $("#hidden_tags").val() + $(this).val();
    $("#hidden_tags").val(newTags);
    console.log($("#hidden_tags").val());
});

// When the "new tag" button is clicked add a comma, unless no tags have been added already
$("#new-entry #new-tag").click(function () {
    if ($("#hidden_tags").val() != "") {
        let newTags = $("#hidden_tags").val() + ",";
        $("#hidden_tags").val(newTags);
        console.log($("#hidden_tags").val());
    }
});

$("#update-username-btn").click(function () {
    toggleField.call(this, "#update-username");
});
$("#update-email-btn").click(function () {
    toggleField.call(this, "#update-email");
});
$("#update-password-btn").click(function () {
    toggleField.call(this, "#update-password");
});

// Initialize tooltips
$("[data-toggle=tooltip]").tooltip();

$(document).ready(function () {
    //Expand all textareas when document is ready
    $("textarea[data-expandable]").each(expandTextArea);

    // Hide the edit tags section on load
    $("#edit-tags").hide();

    // Add a new tag
    $(".add-tag").on("click", addNewTag);

    // Make delete tags deleteable
    $(".delete-tag").each(deleteTag);

    $("#update-username").hide();
    $("#update-email").hide();
    $("#update-password").hide();
});
