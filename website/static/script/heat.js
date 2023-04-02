// set max date to choose

var today = new Date();
var mm = today.getMonth() + 1; //January is 0!
var yyyy = today.getFullYear();

if (mm < 10) {
  mm = '0' + mm;
}
today = yyyy + '-' + mm
document.querySelector("#simpleDate").setAttribute("max", today);
document.querySelector("#advancedDate").setAttribute("max", today);


/* show shape file value after file select */
document.querySelector('.custom-file-input').addEventListener('change', function (e) {
  var fileName = document.getElementById("chooseShapeFile").files[0].name;
  var nextSibling = e.target.nextElementSibling
  nextSibling.innerText = fileName
})

/* show sat images file name*/
document.querySelector('.satInput').addEventListener('change', function (e) {
  var filesName = document.getElementById("chooseSatImg").files;
  var nextSibling = e.target.nextElementSibling
  var innerInputText = ""
  // check if input files are in form
  //B_bandNum.tif ie b_10.tif or B_10.tif
  // .tif is handel by the form
  // B_num or b_num
  // /^[Bb_0-9]*$/ 
  for (let i = 0; i < filesName.length; i++) {
    innerInputText = innerInputText + "||" + filesName[i].name
  }
  innerInputText = innerInputText.substring(2, innerInputText.length);
  nextSibling.innerText = innerInputText
})


// script for profile date list

// get simple option date input

var simpleOptionInputDate = document.querySelector("#simpleDate")
var simpleOptionProfile = document.querySelector("#simpleProfile")
var advancedOptionInputDate = document.querySelector("#advancedDate")
var advancedOptionProfile = document.querySelector("#advancedProfile")

simpleOptionInputDate.addEventListener("change", function (e) {
  // remove all select tag child
  simpleOptionProfile.innerHTML = '';
  createProfileList(simpleOptionInputDate, simpleOptionProfile)
})
advancedOptionInputDate.addEventListener("change", function (e) {
  // remove all select tag child
  advancedOptionProfile.innerHTML = '';
  createProfileList(advancedOptionInputDate, advancedOptionProfile)
})


function addOption(selectTag, value, text) {
  // create option using DOM
  const newOption = document.createElement('option');
  const optionText = document.createTextNode(text);
  // set option text
  newOption.appendChild(optionText);
  // and option value
  newOption.setAttribute('value', value);
  selectTag.appendChild(newOption);
}


function createProfileList(dateTag, selectTag) {
  //console.log(simpleOptionInputDate.value) // year-month 2023-05
  var selectedDate = dateTag.value.split('-');
  var selectedYear = selectedDate[0]
  var selectedMonth = selectedDate[1]

  // calculate the the intervall
  var today = new Date();
  var yyyy = today.getFullYear();



  if (parseInt(selectedYear) == yyyy) // we are in the same choosing year
  {

    // compare the intervalle
    devideInter = parseInt(parseInt(selectedMonth) / 3)

    if (devideInter == 1) {
      addOption(selectTag, "3m", "3 mois")
    }
    else if (devideInter == 2 || devideInter == 3) {
      addOption(selectTag, "3m", "3 mois")
      addOption(selectTag, "6m", "6 mois")
    }
    else if (devideInter == 4) {
      addOption(selectTag, "3m", "3 mois")
      addOption(selectTag, "6m", "6 mois")
      addOption(selectTag, "12m", "12 mois")
    }
  }
  else if (parseInt(selectedYear) < yyyy) {
    addOption(selectTag, "3m", "3 mois")
    addOption(selectTag, "6m", "6 mois")
    addOption(selectTag, "12m", "12 mois")
  }
  else {
    selectTag.innerHTML = '';
  }
}




// set in map behavior


var sLocationInput = document.querySelector("#slocationInput");
var aLocationInput = document.querySelector("#AlocationInput");

const map = document.querySelector("#svgImg");
const states = map.querySelectorAll(".land");

// Expose to window namespase for testing purposes
window.zoomTiger = svgPanZoom(map, {
  zoomEnabled: true,
  controlIconsEnabled: true,
  fit: true,
  center: true,
  //preventMouseEventsDefault: true,
  //onPan: onPanFn,
  beforePan: beforePanFn,
  //onUpdatedCTM: onUpdatedCTMFn,
  onZoom: onZoomFn,
  beforeZoom: beforeZoomFn

});

let isPanning = false;


function beforeZoomFn() {
  console.log('beforeZoomFn')
  isPanning = true;
}


function onZoomFn() {
  console.log('onZoomFn')
  setTimeout(e => {
    isPanning = false;
    console.log('dragend after zoom')
  }, 100)

}


function beforePanFn() {
  isPanning = true;
  console.log('pan')
}

map.addEventListener("mouseup", e => {
  setTimeout(e => {
    isPanning = false;
    console.log('dragend')
  }, 100)

});


states.forEach(function (state, i) {
  state.addEventListener('click', function (e) {
    if (!isPanning) {
      let current = e.currentTarget;
      reset_colors(current);
      current.classList.toggle('on');
      sLocationInput.value = current.getAttribute("name")
      aLocationInput.value = current.getAttribute("name")
    }

  })
})

function reset_colors(exclude) {
  const activeStates = map.querySelectorAll('.on');
  activeStates.forEach(function (state, i) {
    if (state !== exclude) {
      state.classList.remove('on');
    }
  });
}

map.addEventListener('click', function (e) {

  var elemntsWithClassOn = document.getElementsByClassName("on")
  if (elemntsWithClassOn.length == 0) {
    sLocationInput.value = ""
    aLocationInput.value = ""
  }
})

// dropzone handeling
Dropzone.options.dropper = {
  paramName: "file",
  chunking: true,
  forceChunking: true,
  url: "/upload",
  maxFilesize: 1025, // megabytes
  chunkSize: 1000000, // bytes
  maxFiles: 4,
  accept: function(file, done) {
    console.log("uploaded");
    done();
  },
  init: function() {
    this.on("maxfilesexceeded", function(file){
        alert("Le nombre maximum est 4 fichier tif");
    });
  }
};

smsgSpan
simpleBtn = document.getElementById("sbtn")
smsgSpan = document.getElementById("smsgSpan")
simpleBtn.addEventListener('click',function (e)
{


  var target = e.target;
  setTimeout(function()
  {
    target.classList.add('loading');
    smsgSpan.style.display = "block";
  },125);

  // setTimeout(function()
  // {
  //   target.classList.add('ready');
  // },4300);

},false);


advancedBtn = document.getElementById("abtn")

msgSpan = document.getElementById("msgSpan")

advancedBtn.addEventListener('click',function (e)
{

  //console.log("advanced btn clicked")
  
  
  var target = e.target;
  setTimeout(function()
  {
    target.classList.add('loading');
    msgSpan.style.display = "block";

  },125);

  // setTimeout(function()
  // {
  //   target.classList.add('ready');
  // },4300);

},false);


