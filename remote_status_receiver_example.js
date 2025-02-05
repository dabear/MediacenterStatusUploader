const userProperties = PropertiesService.getUserProperties();
const STATUS_OK = "ok";


/**
 * This is a remote status receiver implemented as a google scripts app
 * Why google scripts? Well, it's free ofcourse!
 * Run myFunction() from Script IDE for easy local testing
 * Run POST to the deployed implementation endpoint, using https://github.com/dabear/MediacenterStatusUploader/blob/main/fetcher.py
 * Run notifyBadEntries() from a date based trigger:
 *  Consider to replace the thirtyMinutesAgo variable in getOutDatedOrBadStatuses()
 */

function _verifyAuthentication(providedPassword) {
   //hard coded password, this is just to avoid spam bots really
   const expectedPassword = "SOME_STATIC_STRINGXX";
   return expectedPassword === providedPassword;
}

// this is only used for testing purposes in the google app script editor
function myFunction() {
  /*updateStatus("Plex", "Plex", "ok");
  updateStatus("Plex1", "Plex1", "ok");
  updateStatus("Jackett", "Jackett", "ok");
  updateStatus("Sonarr", "Sonarr", STATUS_OK);
  updateStatus("Deluge", "Deluge", "ok");*/

  console.log(getAllStatuses())
  //console.log(getAllStatusesRaw());
  //notifyBadEntries();

  //console.log("outdated:" + JSON.stringify(outdated))

}
function _sendEmail(subject, body) {
  MailApp.sendEmail({
    to: "your_receiver_replace_me@gmail.com",
    subject: subject,
    htmlBody: body, // HTML content
  });
}

function doPost(e){
  const authstring = e.parameter.authentication;
  const verified = _verifyAuthentication(authstring);

  if (!verified) {
    console.log("not verified");
    return ContentService.createTextOutput("Denied");
  }
  
  if (e.postData && e.postData.contents) {
    var requestData = e.postData.contents; // Raw string data
  } else if(e.parameters.payload) {
    var requestData = e.parameters.payload;
  } else {

     return ContentService.createTextOutput("postdata not received!");
  }
  /*
  
  curl -L -XPOST -H "Content-Type: application/json" -d  '[{"subcomponent": "plex", "program": "plex", "status": "ok"} ]'  https://script.google.com/a/macros/REPLACE_ME/exec?authentication=SOME_STATIC_STRINGXX

  curl -L -XPOST -H "Content-Type: application/json" -d  '[{"subcomponent": "plex", "program": "plex", "status": "ok"}, {"subcomponent": "plex1", "program": "plex1", "status": "ok"} ]'  https://script.google.com/a/macros/REPLACE_ME/exec?authentication=SOME_STATIC_STRINGXX

  
   */
  
  const payloads = JSON.parse(requestData);
 
  for(let i=0; i < payloads.length; i++){

    const payload = payloads[i];
    if(payload.subcomponent && payload.program &&  payload.status) {

      updateStatus(payload.program, payload.subcomponent, payload.status);
    }

  }

}

function notifyBadEntries() {
  const bad = getOutDatedOrBadStatuses();
  console.log(`bad entries: ${JSON.stringify(bad)}`);
  if (bad.length > 0) {

    let body = [];
    let subject = "Found bad statuses, check uptime?";
    for(let i=0; i< bad.length; i++) {
        body.push(`<li>${bad[i].program} - ${bad[i].subcomponent}: ${bad[i].status} (updated: ${bad[i].updated})</li>`);
    }
    
    _sendEmail(subject, "<p>The following statuses were bad or outdated: <ul>"+ body.join("")+"</ul></p>");

  }
}

function getOutDatedOrBadStatuses(){
  const thirtyMinutesAgo = new Date(Date.now() - 30 * 60 * 1000);
  return getAllStatuses().filter( function(o){
    return (o.updated < thirtyMinutesAgo) || o.status != STATUS_OK
  });
}

function getAllStatusesRaw() {
  return userProperties.getProperties();
}

/**
 * Retrieves all user-defined statuses, excluding keys that contain "_GSC".
 * The function parses the keys into program and subcomponent, 
 * and associates each with its status and last updated timestamp.
 *
 * @returns {Array<Object>} An array of status objects, each containing:
 *   - `program` {string}: The program name extracted from the key.
 *   - `subcomponent` {string}: The subcomponent name extracted from the key.
 *   - `status` {string}: The status value associated with the key.
 *   - `updated` {string|null}: The last updated timestamp, if available.
 */
function getAllStatuses() {
  return Object.entries(userProperties.getProperties())
    .filter(([key, value]) => !key.includes("_GSC"))
    .map(([key, value]) => {
      const key2 = key.slice(4); // Removes the first 4 characters
      const [program, subcomponent] = key2.split(/_(.+)/, 2); // Split by first occurance of "_"
      return {
        program: program,
        subcomponent: subcomponent,
        status: value,
        updated: new Date(userProperties.getProperty(`_GSC_updated_${key2}`))
      };
    });
}

function removeStatuses() {
  userProperties.deleteAllProperties();
}

function updateStatus(program_, subcomponent_, newStatus_) {
  program = program_.toLowerCase();
  subcomponent = subcomponent_.toLowerCase();
  newStatus = newStatus_.toLowerCase();

  //GenericUsefulFunctions._sendLogEmail(`calling updateStatus(${program}, ${subcomponent}, ${newStatus})`);
  userProperties.setProperty(`GSC_${program}_${subcomponent}`, newStatus);
  userProperties.setProperty(`_GSC_updated_${program}_${subcomponent}`, new Date());

  
}


