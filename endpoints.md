# Server Endpoints

Here is a list of all the endpoints supported by the server:

- **[<code>POST</code> /register](#register)**
- **[<code>POST</code> /login](#login)**
- **[<code>POST</code> /renewtoken](#renewtoken)**
- **[<code>POST</code> /invalidatetoken](#invalidatetoken)**
- **[<code>POST</code> /fetchlogs](#fetchlogs)**
- **[<code>POST</code> /adds3image](#adds3image)**
- **[<code>POST</code> /addlocationlog](#addlocationlog)**
- **[<code>POST</code> /deletelocationlog](#deletelocationlog)**
- **[<code>POST</code> /fetchminiloclogs](#fetchminiloclogs)**
- **[<code>POST</code> /deletealllocationlogs](#deletealllocationlogs)**
- **<code>POST</code> /updatelocationlog** (Not yet implemented)
- **<code>POST</code> /fetchaccountdetails** (Not yet implemented)

Detailed endpoints list goes here:

## <a name="register"></a> **`POST` /register**

**Methods allowed**: `POST`

**Fields required**: `fullname`, `emailadd`, `username`, `password`

**Possible Responses**:

Status Code: **200 - OK**
```
{"status": "successful"}
```

Status Code: **403 - Forbidden**

```
{"status": "missing_fields"}

{"status": "invalid_email"}

{"status": "username_too_short"}

{"status": "username_has_spaces"}

{"status": "password_too_short"}

{
  "status": "duplicate_username", 
  "username": <duplicate-username>
}

{
  "status": "duplicate_email", 
  "emailadd": <duplicate-email-address>
}
```

Status Code: **500 - Internal Server Error**

```
{"status": "failed"}
```

## <a name="login"></a> **`POST` /login**

**Methods allowed**: `POST`

**Fields required**: `username`, `password`

**Possible Responses**:

Status Code: **200 - OK**

```
{
  "status": "correct_credentials_new_token_generated", 
  "login_token": <new_user_login_token>, 
  "token_expiry": <new_login_token_expiry_epoch_time>, 
  "current_server_time": <current_server_time>
}

{
  "status": "correct_credentials_old_token_passed", 
  "login_token": <old_user_login_token>, 
  "token_expiry": <old_login_token_expiry_epoch_time>
}
```

Status Code: **403 - Forbidden**

```
{"status": "missing_fields"}

{"status": "no_match"}
```

Status Code: **500 - Internal Server Error**

```
{"status": "failed"}
```

## <a name="renewtoken"></a> **`POST` /renewtoken**

**Methods allowed**: `POST`

**Fields required**: `username`, `logintoken`, `logintokenexpiry`

**Possible Responses**:

Status Code: **200 - OK**

```
{
  "status": "renew_success", 
  "new_login_token": <new_user_login_token>, 
  "new_token_expiry": <new_login_token_expiry_epoch_time>, 
  "current_server_time": <current_server_time>
}
```

Status Code: **403 - Forbidden**

```
{"status": "missing_fields"}

{
  "status": "not_renewed", 
  "reason": "no_match"
}

{
  "status": "not_renewed", 
  "reason": "not_needed"
}
```

Status Code: **500 - Internal Server Error**

```
{
  "status": "not_renewed", 
  "reason": "failed"
}
```

## <a name="invalidatetoken"></a> **`POST` /invalidatetoken**

**Methods allowed**: `POST`

**Fields required**: `username`, `logintoken`, `logintokenexpiry`

**Possible Responses**:

Status Code: **200 - OK**

```
{"status": "invalidation_successful"}
```

Status Code: **403 - Forbidden**

```
{"status": "missing_fields"}

{
  "status": "not_invalidated", 
  "reason": "no_match"
}
```

Status Code: **500 - Internal Server Error**

```
{
  "status": "invalidation_failed", 
  "reason": "failed"
}
```

## <a name="fetchlogs"></a> **`POST` /fetchlogs**

**Methods allowed**: `POST`

**Fields required**: none

**Headers required**: Basic Authorization with:

- **username**: username of the user that is trying to access their logs
- **password**: login token issued for that user

**Possible Responses**:

Status Code: **200 - OK**

```
[{
  "publishdate": <location_log_added_epoch>,
  "lastupdateddate": <location_log_last_updated_epoch>,
  "logid": <unique_location_log_id>,
  "title": <title_assoc_with_location_log>,
  "desc": <location_log_description>,
  "images": [
    {
      "s3id": <unique_image_id>,
      "url": <image_amazon_s3_url>,
      "height": <image_height_in_pixels>,
      "width": <image_width_in_pixels>,
      "latlng": <latlng_pair_if_exists_picture_location>,
      "addedtime": <image_added_epoch>
    }, ...
  ],
  "locnames": <list_of_location_names>,
  "locpoints": <list_of_latlng_pair>
}, ...
]
```

Notes:

- Location Names are delimited with `;;;`
- Corresponding Location Points are LatLng pairs of the form `<latitude>,<longitude>` and pairs are delimited with `;`

Status Code: **401 - Unauthorized**

```
{
  "status": "unauthorized", 
  "reason": "missing_auth"
}

{
  "status": "unauthorized", 
  "reason": "invalid_auth"
}
```

## <a name="adds3image"></a> **`POST` /adds3image**

**Methods allowed**: `POST`

**Fields required**: `locationlogid`, `imageurl`, `s3id`, `width`, `height`, `latlng`

**Headers required**: Basic Authorization with:

- **username**: username of the user that is trying to access their logs
- **password**: login token issued for that user

**Possible Responses**:

Status Code: **200 - OK**

```
{
  "status": "success", 
  "uniques3id": <s3id_of_the_added_image>
}
```

Status Code: **401 - Unauthorized**

```
{
  "status": "unauthorized", 
  "reason": "missing_auth"
}

{
  "status": "unauthorized", 
  "reason": "invalid_auth"
}
```

Status Code: **403 - Forbidden**

```
{"status": "missing_fields"}
```

Status Code: **500 - Internal Server Error**

```
{
  "status": "failed",
  "reason": "unable_to_add"
}
```

## <a name="addlocationlog"></a> **`POST` /addlocationlog**

**Methods allowed**: `POST`

**Fields required**: `locationlogid`, `title`, `desc`, `s3ids`, `locnames`, `locpoints`

**Headers required**: Basic Authorization with:

- **username**: username of the user that is trying to access their logs
- **password**: login token issued for that user

**Possible Responses**:

Status Code: **200 - OK**

```
{
  "status": "success",
  "addedate": <server_time_when_the_log_was_added>
}
```

Notes:

- Location names (`locnames`) must be delimited with `;;;`
- Corresponding location points (`locpoints`) must be LatLng pairs of the form `<latitude>,<longitude>` and these pairs must be delimited with `;`
- S3 IDs (`s3ids`) are unique image IDs for this location log and must be delimited with `;`

Status Code: **401 - Unauthorized**

```
{
  "status": "unauthorized", 
  "reason": "missing_auth"
}

{
  "status": "unauthorized", 
  "reason": "invalid_auth"
}
```

Status Code: **403 - Forbidden**

```
{"status": "missing_fields"}
```

## <a name="deletelocationlog"></a> **`POST` /deletelocationlog**

**Methods allowed**: `POST`

**Fields required**: `locationlogid`

**Headers required**: Basic Authorization with:

- **username**: username of the user that is trying to access their logs
- **password**: login token issued for that user

**Possible Responses**:

Status Code: **200 - OK**

```
{"status": "success"}
```

Status Code: **401 - Unauthorized**

```
{
  "status": "unauthorized", 
  "reason": "missing_auth"
}

{
  "status": "unauthorized", 
  "reason": "invalid_auth"
}
```

Status Code: **403 - Forbidden**

```
{"status": "missing_fields"}
```

## <a name="fetchminiloclogs"></a> **`POST` /fetchminiloclogs**

**Methods allowed**: `POST`

**Fields required**: none

**Headers required**: Basic Authorization with:

- **username**: username of the user that is trying to access their logs
- **password**: login token issued for that user

**Possible Responses**:

Status Code: **200 - OK**

```
[{
  "addeddate": <location_log_added_epoch>,
  "lastupdateddate": <location_log_last_updated_epoch>,
  "locationlogid": <unique_location_log_id>,
}, ...
]
```

Status Code: **401 - Unauthorized**

```
{
  "status": "unauthorized", 
  "reason": "missing_auth"
}

{
  "status": "unauthorized", 
  "reason": "invalid_auth"
}
```

## <a name="deletealllocationlogs"></a> **`POST` /deletealllocationlogs**

**Methods allowed**: `POST`

**Fields required**: none

**Headers required**: Basic Authorization with:

- **username**: username of the user that is trying to access their logs
- **password**: login token issued for that user

**Possible Responses**:

Status Code: **200 - OK**

```
{"status": "success"}
```

Status Code: **401 - Unauthorized**

```
{
  "status": "unauthorized", 
  "reason": "missing_auth"
}

{
  "status": "unauthorized", 
  "reason": "invalid_auth"
}
```
