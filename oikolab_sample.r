library(httr)
library(jsonlite)

urlbase <- "https://api.oikolab.com"
weathervars <- c('temperature')

params <- list(
  start = "2020-06-01T00:00:00",
  end = "2021-08-01T00:00:00",
  freq = "H",
  lat = 42.73,
  lon = -76.65,
  `api-key` = "INSERT-API-KEY-HERE"
)

params <- c(params, setNames(as.list(weathervars), rep('param', length(weathervars))))

resp <- httr::GET(url = urlbase, query = params, path = c('weather'))
httr::stop_for_status(resp)
content <- httr::content(resp, as = "parsed")
out <- jsonlite::fromJSON(content$data)
outdf <- as.data.frame(out$data)
colnames(outdf) <- out$columns
outdf$timestamp <- as.POSIXct(out$index, origin = '1970-01-01', tz = 'UTC')
outdf
