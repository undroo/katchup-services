# Sponti Backend API Reference

Base URL: `http://localhost:8000` (Local development)

## Authentication

All endpoints requiring authentication expect a Bearer token in the `Authorization` header:
`Authorization: Bearer <your_jwt_token>`

### Auth Endpoints

#### Login with Google
**POST** `/auth/google`
- **Description**: Authenticate user with Google OAuth token. Creates a new user if they don't exist.
- **Request Body**: `GoogleTokenRequest`
  ```json
  {
    "token": "string"
  }
  ```
- **Response**: `LoginResponse`
  ```json
  {
    "access_token": "string",
    "token_type": "bearer",
    "user": { ... }
  }
  ```

#### Get Current User
**GET** `/auth/me`
- **Description**: Get the profile of the currently authenticated user.
- **Auth Required**: Yes
- **Response**: `UserResponse`

---

## Users

### Profile Management

#### Get User Profile
**GET** `/users/profile`
- **Description**: Get full user profile with interests, preferences, and saved places.
- **Auth Required**: Yes
- **Response**: `UserProfileResponse`

#### Search Users
**GET** `/users/search`
- **Description**: Search users by name or email (for adding friends). Returns users matching the query who are not already friends and have no pending request. Excludes the current user.
- **Auth Required**: Yes
- **Query Parameters**: `q` (required, min 2 characters)
- **Response**: List of user summaries
  ```json
  [
    {
      "id": "string",
      "name": "string",
      "email": "string",
      "picture": "string | null"
    }
  ]
  ```
- **Logic**: Partial match on `name` or `email` (case-insensitive). Limit 20 results.

#### Update User Settings
**PATCH** `/users/settings`
- **Description**: Update user configuration settings.
- **Auth Required**: Yes
- **Request Body**: `UserSettingsUpdate`
  ```json
  {
    "auto_sync_calendar_on_join": boolean
  }
  ```
- **Response**: `UserSettingsResponse`

#### Get User Settings
**GET** `/users/settings`
- **Description**: Get user configuration settings.
- **Auth Required**: Yes
- **Response**: `UserSettingsResponse`

#### Update Interests
**PATCH** `/users/profile/interests`
- **Auth Required**: Yes
- **Request Body**: `UserInterestsUpdate`
  ```json
  {
    "interests": ["string"]
  }
  ```
- **Response**: `UserProfileResponse`

#### Update Preferences
**PATCH** `/users/profile/preferences`
- **Auth Required**: Yes
- **Request Body**: `UserPreferencesUpdate`
  ```json
  {
    "preferences": UserPreferences
  }
  ```
  *(See `USER_PREFERENCES_SCHEMA.md` for full `UserPreferences` object structure)*
- **Response**: `UserProfileResponse`

#### Update Saved Places
**PATCH** `/users/profile/saved-places`
- **Auth Required**: Yes
- **Request Body**: `UserSavedPlacesUpdate`
  ```json
  {
    "saved_places": ["string"]
  }
  ```
- **Response**: `UserProfileResponse`

#### Update Locations
**PATCH** `/users/profile/locations`
- **Auth Required**: Yes
- **Request Body**: `UserLocationsUpdate`
  ```json
  {
    "locations": ["string"]
  }
  ```
- **Response**: `UserProfileResponse`

### User Availability

User-defined availability rules for times the user wants to keep free. Supports recurring patterns and one-off exceptions. Used for finding magic windows with circles and group scheduling.

#### Get Availability Patterns
**GET** `/users/me/availability/patterns`
- **Description**: List all availability patterns for the current user.
- **Auth Required**: Yes
- **Response**: List of `AvailabilityPatternResponse`

#### Create Availability Pattern
**POST** `/users/me/availability/patterns`
- **Auth Required**: Yes
- **Request Body**: `AvailabilityPatternCreate`
  ```json
  {
    "name": "string",
    "start_time": "HH:mm",
    "end_time": "HH:mm",
    "recurrence_type": "once" | "daily" | "weekly" | "custom",
    "days_of_week": [1, 2, 3, 4, 5],
    "start_date": "YYYY-MM-DD",
    "end_date": "YYYY-MM-DD",
    "is_active": true,
    "slot_type": "free" | "busy"
  }
  ```
  - `days_of_week`: 1=Monday .. 7=Sunday (for `weekly`/`custom`)
  - `start_date`/`end_date`: optional validity range
  - `slot_type`: `free` = available time, `busy` = blocked time (default: `free`)
- **Response**: `AvailabilityPatternResponse` (includes generated `id`)

#### Update Availability Pattern
**PUT** `/users/me/availability/patterns/{id}`
- **Auth Required**: Yes
- **Request Body**: Same as create
- **Response**: `AvailabilityPatternResponse`

#### Delete Availability Pattern
**DELETE** `/users/me/availability/patterns/{id}`
- **Auth Required**: Yes
- **Response**: JSON Message

#### Get Availability Exceptions
**GET** `/users/me/availability/exceptions`
- **Description**: List availability exceptions. Optional date filter.
- **Query Params**: `from` (YYYY-MM-DD), `to` (YYYY-MM-DD)
- **Auth Required**: Yes
- **Response**: List of `AvailabilityExceptionResponse`

#### Create Availability Exception
**POST** `/users/me/availability/exceptions`
- **Auth Required**: Yes
- **Request Body**: `AvailabilityExceptionCreate`
  ```json
  {
    "date": "YYYY-MM-DD",
    "start_time": "HH:mm",
    "end_time": "HH:mm",
    "name": "string",
    "rule_id": "string",
    "slot_type": "free" | "busy"
  }
  ```
  - `name`, `rule_id` optional
  - `slot_type`: optional, default `"free"`. `"free"` = available time, `"busy"` = blocked time
- **Response**: `AvailabilityExceptionResponse`

#### Update Availability Exception
**PUT** `/users/me/availability/exceptions/{id}`
- **Auth Required**: Yes
- **Request Body**: Same as create
- **Response**: `AvailabilityExceptionResponse`

#### Delete Availability Exception
**DELETE** `/users/me/availability/exceptions/{id}`
- **Auth Required**: Yes
- **Response**: JSON Message

**AvailabilityExceptionResponse** fields:

| Field | Type | Description |
|-------|------|-------------|
| `id` | string (UUID) | Unique exception ID |
| `user_id` | string (UUID) | Owner |
| `date` | string | YYYY-MM-DD |
| `start_time` | string | HH:mm (24h) |
| `end_time` | string | HH:mm (24h) |
| `name` | string \| null | Optional label |
| `rule_id` | string \| null | Optional pattern reference |
| `slot_type` | string | `"free"` = available time, `"busy"` = blocked time |
| `created_at` | string (ISO datetime) | Creation timestamp |
| `updated_at` | string (ISO datetime) | Last update timestamp |

#### Get Effective Availability
**GET** `/users/me/availability/effective`
- **Description**: Computed free slots for a date or range, merging patterns and exceptions. Exceptions override patterns. Optionally excludes synced calendar busy times.
- **Query Params**: either `date=YYYY-MM-DD` or `from=YYYY-MM-DD&to=YYYY-MM-DD`; `exclude_calendar` (bool, default true)
- **Auth Required**: Yes
- **Response**: List of `{ "start": "HH:mm", "end": "HH:mm", "date": "YYYY-MM-DD" }` (date present when querying a range)

**Conflict resolution**: For a given date: (1) expand active patterns into free intervals, (2) apply exceptions — free exceptions add/replace free intervals, busy exceptions subtract from free time, (3) exclude calendar busy times if `exclude_calendar=true`.

---

## Friends

#### Send Friend Request
**POST** `/friends/request`
- **Auth Required**: Yes
- **Request Body**: `FriendRequest`
  ```json
  {
    "friend_email": "string"
  }
  ```
- **Response**: `FriendResponse`

#### Get Friend Requests
**GET** `/friends/requests`
- **Description**: Get all incoming and outgoing friend requests.
- **Auth Required**: Yes
- **Response**: List of `FriendRequestResponse`

#### Accept Friend Request
**PUT** `/friends/{friendship_id}/accept`
- **Auth Required**: Yes
- **Response**: `FriendResponse`

#### Decline Friend Request
**PUT** `/friends/{friendship_id}/decline`
- **Auth Required**: Yes
- **Response**: JSON Message

#### Get Friends
**GET** `/friends`
- **Description**: Get all accepted friends.
- **Auth Required**: Yes
- **Response**: List of `FriendResponse`

#### Remove Friend
**DELETE** `/friends/{friendship_id}`
- **Auth Required**: Yes
- **Response**: JSON Message

---

## Groups

#### Create Group
**POST** `/groups`
- **Auth Required**: Yes
- **Request Body**: `GroupCreate`
  ```json
  {
    "name": "string",
    "description": "string",
    "interests": ["string"],
    "preferences": ["string"]
  }
  ```
- **Response**: `GroupResponse`

#### Get User's Groups
**GET** `/groups`
- **Description**: Get all groups the user is a member of.
- **Auth Required**: Yes
- **Response**: List of `GroupResponse`

#### Get Specific Group
**GET** `/groups/{group_id}`
- **Auth Required**: No
- **Response**: `GroupResponse`

#### Add Group Member
**POST** `/groups/{group_id}/members`
- **Auth Required**: Yes (Admin only)
- **Request Body**: `GroupMemberAdd`
  ```json
  {
    "user_email": "string"
  }
  ```
- **Response**: JSON Message

#### Remove Group Member
**DELETE** `/groups/{group_id}/members/{user_id}`
- **Auth Required**: Yes (Admin or self)
- **Response**: JSON Message

#### Delete Group
**DELETE** `/groups/{group_id}`
- **Auth Required**: Yes (Creator only)
- **Response**: JSON Message

#### Update Group Interests
**PATCH** `/groups/{group_id}/interests`
- **Auth Required**: Yes (Member)
- **Request Body**: `GroupInterestsUpdate`
- **Response**: `GroupResponse`

#### Update Group Preferences
**PATCH** `/groups/{group_id}/preferences`
- **Auth Required**: Yes (Member)
- **Request Body**: `GroupPreferencesUpdate`
- **Response**: `GroupResponse`

#### Get Group Availability
**GET** `/groups/{group_id}/availability`
- **Description**: Get common free time slots for group members. Uses each member's effective availability (patterns + exceptions minus calendar busy times).
- **Query Params**: `duration` (int, default 60)
- **Auth Required**: Yes
- **Response**: `AvailabilityResponse`

#### Check Availability (by User Emails)
**POST** `/availability/check`
- **Description**: Get common free time slots for a list of users by email. Same format as group availability. Emails not in the system are omitted.
- **Auth Required**: Yes
- **Request Body**:
  ```json
  {
    "user_emails": ["string"],
    "duration": 120
  }
  ```
- **Response**: `AvailabilityResponse`

**AvailabilityResponse** (flat list, one object per time slot):
| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `date` | string | Yes | YYYY-MM-DD |
| `start_time` | string | Yes | HH:mm (24h) |
| `end_time` | string | Yes | HH:mm (24h) |
| `members_available` | int | Optional | Number of people free in this slot |
| `total_members` | int | Optional | Total group size |

Example:
```json
{
  "available_slots": [
    { "date": "2026-03-07", "start_time": "09:00", "end_time": "12:00", "members_available": 2, "total_members": 2 },
    { "date": "2026-03-07", "start_time": "14:00", "end_time": "17:00", "members_available": 2, "total_members": 2 }
  ]
}
```

---

## Events

#### Get All Events
**GET** `/events`
- **Description**: Get all events (system wide or accessible).
- **Auth Required**: No
- **Query Parameters (optional):**
  - `upcoming` (boolean, default: false): When true, only returns events that haven't ended yet.
  - `limit` (integer, 1-500, optional): Maximum number of events to return.
- **Response**: List of `EventResponse`

#### Create Event
**POST** `/events`
- **Auth Required**: Yes
- **Request Body**: `EventCreate`
- **Response**: `EventResponse`

#### Get Specific Event
**GET** `/events/{event_id}`
- **Auth Required**: No
- **Response**: `EventResponse`

#### Update Event
**PUT** `/events/{event_id}`
- **Auth Required**: No
- **Request Body**: `EventUpdate`
- **Response**: `EventResponse`

#### Delete Event
**DELETE** `/events/{event_id}`
- **Auth Required**: No
- **Response**: JSON Message

#### Get Invited Events
**GET** `/events/invited/{email}`
- **Description**: Get events where the user (by email) is invited.
- **Auth Required**: No
- **Response**: List of `EventResponse`

### Event Attendance

#### Confirm Attendance
**POST** `/events/{event_id}/attend`
- **Auth Required**: Optional (User tracking if logged in)
- **Request Body**: `AttendanceRequest`
  ```json
  {
    "name": "string",
    "email": "string",
    "mobile": "string"
  }
  ```
- **Response**: `EventResponse`

#### Cancel Attendance
**DELETE** `/events/{event_id}/cancel/{attendee_email}`
- **Auth Required**: Optional
- **Response**: JSON Message

#### Cancel Attendance with Calendar Sync
**POST** `/events/{event_id}/cancel-with-calendar/{attendee_email}`
- **Description**: Cancel attendance and attempt to remove from Google Calendar.
- **Auth Required**: Optional
- **Response**: JSON Message

### Event Invitations

#### Send Invitation
**POST** `/events/{event_id}/invite`
- **Request Body**: `InvitationRequest`
- **Response**: `InvitationResponse`

#### Send Bulk Invitations
**POST** `/events/{event_id}/invite/bulk`
- **Request Body**: List of `InvitationRequest`
- **Response**: List of `InvitationResponse`

#### Respond to Invitation
**PUT** `/events/{event_id}/invite/{email}/respond`
- **Request Body**: JSON `{ "status": "confirmed" | "declined" }`
- **Response**: JSON Message

### Scheduling poll (proposed slots & votes)

`EventResponse`, `EventCreate`, and `EventUpdate` include optional scheduling poll fields (all nullable / omit on read when unset):

- `scheduling_poll_closes_at` (ISO datetime or null)
- `scheduling_poll_mode` (`single` | `multi` or null; app default is typically `multi`)
- `scheduling_status` (`open` | `closed` | `confirmed` or null)

Updating these fields via **PUT** `/events/{event_id}` requires authentication as the **event host** (`created_by`). Other event fields keep existing behavior.

#### List proposed slots
**GET** `/events/{event_id}/proposed-slots`
- **Auth Required**: No
- **Response**: Array of `ProposedSlotListItem` — each slot includes `vote_count`, `voter_user_ids`, and `voter_guest_ids` for UI (avatars / agreement counts).
- **Default slot**: If the event has **no** proposed slots yet and the event has a host (`created_by`), the first successful list request **creates** one slot from the event `date_time` and `end_time` (or a one-hour window when `end_time` is missing or invalid). `source` is `initial`. Still returns **404** if the event row does not exist.

#### Create proposed slot (authenticated user)
**POST** `/events/{event_id}/proposed-slots`
- **Auth Required**: Yes
- **Request Body**: `{ "start_at": ISO datetime, "end_at": ISO datetime, "label"?: string, "source"?: string }`
- **Access**: Event host, group member (if event has a group), or attendee (matched by `user_id` or email).
- **Response**: `ProposedSlotListItem` (201)

#### Delete proposed slot (authenticated user)
**DELETE** `/events/{event_id}/proposed-slots/{slot_id}`
- **Auth Required**: Yes
- **Access**: Event host or the user who created the slot.

#### Vote on a slot (authenticated user)
**POST** `/events/{event_id}/proposed-slots/{slot_id}/vote`
- **Auth Required**: Yes
- **Access**: Same as create slot.
- **Behavior**: If `scheduling_poll_mode` is `single`, other votes by this user on other slots for the same event are removed first.
- **Response**: `ProposedSlotListItem` for the voted slot.

#### Remove vote (authenticated user)
**DELETE** `/events/{event_id}/proposed-slots/{slot_id}/vote`
- **Auth Required**: Yes
- **Response**: `{ "status": "ok" }`

---

## Notifications

Event-related notifications: event updates (when someone else changes an event you're attending), event invites, and invite acceptances.

### Response Shapes

- **NotificationResponse**: id, type, read_at?, created_at, ref_event_id?, ref_actor_id?, extra (object)

### Endpoints

#### List Notifications
**GET** `/notifications`
- **Description**: List current user's notifications. Unread first, then by created_at DESC.
- **Auth Required**: Yes
- **Query Parameters**: `limit` (default 50, max 100), `offset` (default 0), `unread_only` (optional, default false)
- **Response**: List of `NotificationResponse`

#### Get Unread Count
**GET** `/notifications/unread-count`
- **Description**: Get unread notification count for badge display.
- **Auth Required**: Yes
- **Response**: JSON `{ "count": number }`

#### Mark Notification as Read
**PATCH** `/notifications/{notification_id}/read`
- **Auth Required**: Yes
- **Response**: JSON `{ "status": "ok" }`

#### Mark All Notifications as Read
**PATCH** `/notifications/read-all`
- **Auth Required**: Yes
- **Response**: JSON `{ "status": "ok" }`

---

## Group Events & Recommendations

#### Get Group Events
**GET** `/groups/{group_id}/events`
- **Description**: Get events for a specific group within one week from today (default, optimized endpoint).
- **Auth Required**: Yes
- **Response**: List of `EventResponse`

#### Get All Group Events
**GET** `/groups/{group_id}/events/all`
- **Description**: Get all events for a specific group (no date filter). Use this endpoint when you need the complete event history.
- **Auth Required**: Yes
- **Response**: List of `EventResponse`

#### Create Group Event
**POST** `/groups/{group_id}/events`
- **Auth Required**: Yes
- **Request Body**: `EventCreate`
- **Response**: `EventResponse`

#### Get Group Recommendations
**GET** `/groups/{group_id}/recommendations`
- **Auth Required**: Yes
- **Response**: List of `RecommendedEventResponse`

#### Create Recommendation
**POST** `/groups/{group_id}/recommendations`
- **Auth Required**: Yes
- **Request Body**: `RecommendedEventCreate`
- **Response**: `RecommendedEventResponse`

#### Accept Recommendation
**POST** `/groups/{group_id}/recommendations/{rec_id}/accept`
- **Description**: Converts a recommendation into a real event.
- **Auth Required**: Yes
- **Response**: `EventResponse`

#### Dismiss Recommendation
**POST** `/groups/{group_id}/recommendations/{rec_id}/dismiss`
- **Auth Required**: Yes
- **Response**: JSON Message

#### Get All User Recommendations
**GET** `/recommendations/all`
- **Description**: Get recommendations across all groups the user belongs to.
- **Auth Required**: Yes
- **Response**: List of `RecommendedEventWithGroupResponse`

#### Get User Recommendations (Detailed)
**GET** `/users/me/recommendations`
- **Description**: Get recommendations with full group details.
- **Auth Required**: Yes
- **Response**: List of `UserRecommendedEventResponse`

---

## Kai AI Assistant

**GET** `/kai/status`
- **Description**: Check if the AI service is initialized and ready.
- **Auth Required**: No
- **Response**: JSON `{ "status": "ready" | "error", "message": "string" }`

---

## Conversations (Messaging)

Human-to-human chat: direct messages (friends only), group chats, and event chats.

### Response Shapes

- **ConversationUserSummary**: `{ id, name, picture? }` — minimal user info for display
- **ConversationListItemResponse**: id, type, group_id?, event_id?, name?, last_message?, last_message_at?, unread_count, **other_participants** (list of ConversationUserSummary — participants excluding current user)
- **ConversationParticipantResponse**: id, user_id?, ai_agent?, role, joined_at, **user?** (ConversationUserSummary when human participant)
- **ConversationMessageResponse**: id, conversation_id, sender_id?, sender_ai_agent?, content, created_at, **sender_name?**, **sender_picture?**

### Conversations

#### List Conversations
**GET** `/conversations`
- **Description**: List conversations for the current user with last message, unread count, and other participants (who you're chatting with).
- **Auth Required**: Yes
- **Response**: List of `ConversationListItemResponse`

#### Get Conversation
**GET** `/conversations/{id}`
- **Description**: Get conversation details and participants (with name, picture for each).
- **Auth Required**: Yes
- **Response**: `ConversationResponse`

#### Get or Create Direct Conversation
**POST** `/conversations/direct`
- **Description**: Get or create a DM with a friend. Requires accepted friendship.
- **Auth Required**: Yes
- **Request Body**: `{ "friend_id": "uuid" }`
- **Response**: `ConversationResponse`

#### Get or Create Group Conversation
**POST** `/conversations/group/{group_id}`
- **Description**: Get or create group chat. Requires group membership.
- **Auth Required**: Yes
- **Response**: `ConversationResponse`

#### Get or Create Event Conversation
**POST** `/conversations/event/{event_id}`
- **Description**: Get or create event chat. Requires creator, group member, or attendee.
- **Auth Required**: Yes
- **Response**: `ConversationResponse`

#### Mark as Read
**PATCH** `/conversations/{id}/read`
- **Auth Required**: Yes
- **Response**: `{ "status": "ok" }`

### Messages

#### Get Messages
**GET** `/conversations/{id}/messages`
- **Description**: Paginated messages with sender name and picture. Query params: `before_id`, `limit` (default 50).
- **Auth Required**: Yes
- **Response**: List of `ConversationMessageResponse` (includes sender_name, sender_picture)

#### Send Message
**POST** `/conversations/{id}/messages`
- **Auth Required**: Yes
- **Request Body**: `{ "content": "string" }`
- **Response**: `ConversationMessageResponse` (includes sender_name, sender_picture)
- **Side-effect**: After inserting, the backend sends a Supabase Realtime **Broadcast** on channel `conversation:{id}` with event `new_message` containing the full message payload (see Realtime section below). Additionally, Supabase Realtime fires a **Postgres Changes** INSERT event on `conversation_messages` automatically.

#### Send Typing Indicator
**POST** `/conversations/{id}/typing`
- **Description**: Broadcast a typing indicator to other participants. Ephemeral — nothing is stored in the database.
- **Auth Required**: Yes
- **Response**: `{ "status": "ok" }`
- **Side-effect**: Sends a Supabase Realtime Broadcast on channel `conversation:{id}` with event `typing`:
  ```json
  {
    "user_id": "uuid",
    "user_name": "string"
  }
  ```

### Supabase Realtime (Recommended)

The backend publishes live chat events via **Supabase Realtime**. Frontends should subscribe to these channels for instant message delivery instead of polling REST endpoints.

#### Prerequisites

Supabase Realtime must be enabled on the `conversation_messages` and `conversations` tables (see `migration_enable_realtime_chat.sql`).

#### Channel Naming

| Channel name | Purpose |
|---|---|
| `conversation:{conversation_id}` | Broadcast events for a single conversation (new messages, typing indicators) |

#### Subscribing to Messages (Postgres Changes)

Subscribe to INSERT events on `conversation_messages` filtered by `conversation_id`. This fires automatically whenever a row is inserted — no backend relay needed.

```javascript
// Example using supabase-js
const channel = supabase
  .channel('conversation:' + conversationId)
  .on(
    'postgres_changes',
    {
      event: 'INSERT',
      schema: 'public',
      table: 'conversation_messages',
      filter: `conversation_id=eq.${conversationId}`,
    },
    (payload) => {
      // payload.new contains the new message row
      // Note: does NOT include sender_name/sender_picture (raw DB row).
      // Use the Broadcast event below for enriched data, or look up locally.
    }
  )
  .subscribe();
```

#### Subscribing to Broadcasts (Enriched Messages + Typing)

The backend also sends **Broadcast** events on the same channel with enriched payloads (includes sender_name, sender_picture). Subscribe to these for the best UX:

```javascript
const channel = supabase
  .channel('conversation:' + conversationId)
  .on('broadcast', { event: 'new_message' }, (payload) => {
    // payload.payload = { id, conversation_id, sender_id, content, created_at,
    //                      sender_name, sender_picture, sender_ai_agent }
  })
  .on('broadcast', { event: 'typing' }, (payload) => {
    // payload.payload = { user_id, user_name }
  })
  .subscribe();
```

**Recommended pattern**: Subscribe to both Postgres Changes (reliable, guaranteed delivery) and Broadcast (fast, enriched). De-duplicate by message `id`.

#### Subscribing to Conversation List Updates

To refresh the conversation list when any conversation receives a new message, subscribe to UPDATE events on the `conversations` table:

```javascript
supabase
  .channel('conversations-updates')
  .on(
    'postgres_changes',
    { event: 'UPDATE', schema: 'public', table: 'conversations' },
    () => {
      // Re-fetch GET /conversations to update last_message, unread_count, ordering
    }
  )
  .subscribe();
```

### WebSocket (Deprecated)

> **Deprecated**: Use the Supabase Realtime channels described above instead. The legacy WebSocket will be removed in a future release.

**WS** `/ws/chat?token=<jwt>`
- **Description**: Legacy real-time chat relay. Connect with JWT in query. Send `{"type": "subscribe", "conversation_id": "uuid"}` to receive new messages for that conversation.
- **Auth Required**: Yes (token in query)

---

## Bucket List

#### Create Bucket List Item
**POST** `/bucket-list`
- **Auth Required**: Yes
- **Request Body**: `BucketListItemCreate`
  ```json
  {
    "title": "string",
    "description": "string",
    "timeframe": "string",
    "location": "string"
  }
  ```
- **Response**: `BucketListItemResponse`

#### Get Bucket List
**GET** `/bucket-list`
- **Auth Required**: Yes
- **Response**: List of `BucketListItemResponse`

#### Get Item
**GET** `/bucket-list/{item_id}`
- **Auth Required**: Yes
- **Response**: `BucketListItemResponse`

#### Update Item
**PUT** `/bucket-list/{item_id}`
- **Auth Required**: Yes
- **Request Body**: `BucketListItemUpdate`
- **Response**: `BucketListItemResponse`

#### Delete Item
**DELETE** `/bucket-list/{item_id}`
- **Auth Required**: Yes
- **Response**: JSON Message

---

## Collections

#### Get Collections
**GET** `/collections`
- **Description**: Get all collections for the current user with idea counts.
- **Auth Required**: Yes
- **Response**: List of `CollectionResponse`
  ```json
  [
    {
      "id": "string",
      "user_id": "string",
      "name": "string",
      "is_default": true,
      "created_at": "datetime",
      "idea_count": 5
    }
  ]
  ```

#### Create Collection
**POST** `/collections`
- **Description**: Create a new collection for organizing saved ideas.
- **Auth Required**: Yes
- **Request Body**: `CollectionCreate`
  ```json
  {
    "name": "string"
  }
  ```
- **Response**: `CollectionResponse`

#### Update Collection
**PUT** `/collections/{collection_id}`
- **Description**: Update a collection's name.
- **Auth Required**: Yes
- **Request Body**: `CollectionUpdate`
  ```json
  {
    "name": "string (optional)"
  }
  ```
- **Response**: `CollectionResponse`

#### Delete Collection
**DELETE** `/collections/{collection_id}?keep_ideas=true`
- **Description**: Delete a collection. Cannot delete the default collection.
- **Auth Required**: Yes
- **Query Parameters**:
  - `keep_ideas` (boolean, optional, default: `true`): If `true`, all ideas in the collection will be moved to the default collection. If `false`, all ideas will be deleted along with the collection.
- **Response**: JSON Message
  ```json
  {
    "message": "Collection deleted successfully. Ideas were moved to default collection."
  }
  ```
  or
  ```json
  {
    "message": "Collection deleted successfully. Ideas were deleted."
  }
  ```

#### Get Collection Ideas
**GET** `/collections/{collection_id}/ideas`
- **Description**: Get all ideas in a specific collection. Accessible by the collection owner or users the collection is shared with.
- **Auth Required**: Yes
- **Response**: List of `SavedIdeaResponse`

### Collection Sharing

#### Get Shared Collections
**GET** `/collections/shared-with-me`
- **Description**: Get all collections shared with the current user, including owner info and permission level.
- **Auth Required**: Yes
- **Response**: List of `SharedCollectionResponse`
  ```json
  [
    {
      "id": "string",
      "user_id": "string",
      "name": "string",
      "is_default": false,
      "created_at": "datetime",
      "idea_count": 5,
      "permission": "view",
      "shared_by": {
        "id": "string",
        "name": "string",
        "picture": "string"
      }
    }
  ]
  ```

#### Share Collection
**POST** `/collections/{collection_id}/share`
- **Description**: Share a collection with a friend. Only non-default collections can be shared, and the target user must be an accepted friend.
- **Auth Required**: Yes
- **Request Body**: `ShareCollectionRequest`
  ```json
  {
    "shared_with_user_id": "string",
    "permission": "view"
  }
  ```
  - `permission`: `"view"` (default) or `"edit"`
- **Response**: `CollectionShareResponse`
  ```json
  {
    "id": "string",
    "collection_id": "string",
    "shared_with_user_id": "string",
    "shared_by_user_id": "string",
    "permission": "view",
    "created_at": "datetime",
    "shared_with_user": {
      "id": "string",
      "name": "string",
      "picture": "string"
    }
  }
  ```

#### Get Collection Shares
**GET** `/collections/{collection_id}/shares`
- **Description**: Get all users a collection is shared with. Only the collection owner can view shares.
- **Auth Required**: Yes
- **Response**: List of `CollectionShareResponse`

#### Update Collection Share
**PUT** `/collections/{collection_id}/shares/{share_id}`
- **Description**: Update the permission level of a collection share. Only the collection owner can update.
- **Auth Required**: Yes
- **Request Body**: `UpdateShareRequest`
  ```json
  {
    "permission": "edit"
  }
  ```
- **Response**: `CollectionShareResponse`

#### Remove Collection Share
**DELETE** `/collections/{collection_id}/shares/{share_id}`
- **Description**: Remove a collection share. The collection owner can unshare, or the shared-with user can remove themselves.
- **Auth Required**: Yes
- **Response**: JSON Message
  ```json
  {
    "message": "Share removed successfully"
  }
  ```

---

## Saved Ideas

Saved ideas support content from external sources (share sheets, links). The backend **enriches** incoming data by fetching preview metadata and detecting the content source when the frontend sends minimal info.

### Backend enrichment (Create endpoint)

When you create a saved idea, the backend will:
- **Fill missing fields** – If `url` is provided and `name`, `description`, or `preview_image_url` are empty, the backend fetches Open Graph / metadata (or yt-dlp for social media) and populates them.
- **Detect source** – If `source` is generic (`ios_share_extension`), the backend infers it from the URL and returns a canonical value for icon display.
- **Google Place ID** – For Google Maps URLs, the backend attempts to extract `google_place_id` when not provided.

You can send minimal payload (e.g. `name` + `url` from a share sheet); the backend will fill preview data where possible. Frontend-provided values are preferred; enrichment only fills gaps.

### Source values (for icon mapping)

The `source` field in responses uses these canonical values for display:

| Value | Use case | Suggested icon |
|-------|----------|----------------|
| `instagram` | Instagram posts/reels | Instagram logo |
| `tiktok` | TikTok videos | TikTok logo |
| `google` | Google Maps links | Google Maps icon |
| `youtube` | YouTube videos | YouTube logo |
| `twitter` | Twitter/X posts | Twitter/X logo |
| `ios_share_extension` | Share sheet, unknown | Generic link icon |

### Response fields (what the frontend receives)

All `SavedIdeaResponse` objects include:

| Field | Type | Description |
|-------|------|-------------|
| `id` | string (UUID) | Unique idea ID |
| `user_id` | string (UUID) | Owner |
| `collection_id` | string (UUID) | Collection this idea belongs to |
| `name` | string | Title (required; backend uses "Untitled idea" if missing) |
| `url` | string \| null | Link to source content |
| `text` | string \| null | User notes / caption |
| `description` | string \| null | Preview description or combined notes |
| `preview_image_url` | string \| null | Thumbnail or og:image (for videos, this is the video thumbnail) |
| `categories` | string[] | Categories (default `[]`) |
| `tags` | string[] | Tags (default `[]`) |
| `source` | string | Canonical source for icon (see table above) |
| `google_place_id` | string \| null | Google Place ID (for Maps URLs) |
| `created_at` | string (ISO datetime) | Creation timestamp |

---

#### Get Saved Ideas
**GET** `/saved_ideas`
- **Description**: Get all saved ideas for the current user across all collections.
- **Auth Required**: Yes
- **Response**: List of `SavedIdeaResponse` (see fields above)

#### Create Saved Idea
**POST** `/saved_ideas`
- **Description**: Save content shared from external sources (e.g., iOS Share Extension). Backend enriches with preview metadata when `url` is provided and name/description/preview_image_url are missing. If no collection_id is provided, the idea is added to the user's default collection.
- **Auth Required**: Yes
- **Request Body**: `SavedIdeaCreate`
  ```json
  {
    "name": "string (required, but can be empty; backend fills from preview if url provided)",
    "url": "string (optional) - triggers preview fetch when name/description/preview_image_url missing",
    "text": "string (optional) - user notes / caption",
    "description": "string (optional) - combined preview description + notes",
    "preview_image_url": "string (optional) - from /api/preview; backend fills if missing and url provided",
    "categories": ["string"],
    "tags": ["string"],
    "google_place_id": "string (optional) - auto-extracted for Google Maps URLs",
    "source": "string (optional, default: ios_share_extension) - backend infers from URL when generic",
    "collection_id": "string (optional) - defaults to user's default collection"
  }
  ```
- **Minimal request example** (share sheet with URL only):
  ```json
  {
    "name": "",
    "url": "https://www.instagram.com/p/abc123/"
  }
  ```
  Backend will fetch preview and populate `name`, `description`, `preview_image_url`, and set `source` to `instagram`.
- **Response**: JSON Object
  ```json
  {
    "status": "success",
    "data": {
        "id": "string",
        "user_id": "string",
        "collection_id": "string",
        "name": "string",
        "url": "string | null",
        "text": "string | null",
        "description": "string | null",
        "preview_image_url": "string | null",
        "categories": ["string"],
        "tags": ["string"],
        "source": "string",
        "google_place_id": "string | null",
        "created_at": "string"
    }
  }
  ```

#### Update Saved Idea
**PUT** `/saved_ideas/{idea_id}`
- **Description**: Update a saved idea. Allowed if the user owns the idea or has edit permission on its collection.
- **Auth Required**: Yes
- **Request Body**: `SavedIdeaUpdate` (all fields optional for partial updates)
  ```json
  {
    "name": "string (optional)",
    "url": "string (optional)",
    "text": "string (optional)",
    "description": "string (optional)",
    "preview_image_url": "string (optional)",
    "categories": ["string"] (optional),
    "tags": ["string"] (optional),
    "collection_id": "string (optional) - move to another collection",
    "google_place_id": "string (optional)"
  }
  ```
- **Response**: `SavedIdeaResponse`

#### Move Saved Idea
**PUT** `/saved_ideas/{idea_id}/move`
- **Description**: Move a saved idea to a different collection.
- **Auth Required**: Yes
- **Request Body**: `MoveIdeaRequest`
  ```json
  {
    "collection_id": "string"
  }
  ```
- **Response**: `SavedIdeaResponse`

#### Delete Saved Idea
**DELETE** `/saved_ideas/{idea_id}`
- **Description**: Delete a saved idea. Allowed if the user owns the idea or has edit permission on its collection.
- **Auth Required**: Yes
- **Response**: `{"message": "Saved idea deleted successfully"}`

---

## Calendar Integration

#### Get Calendar Status
**GET** `/calendar/status`
- **Auth Required**: Yes
- **Response**: `CalendarStatusResponse`

#### Get Auth URL
**GET** `/calendar/auth-url`
- **Description**: Get the Google OAuth URL to authorize calendar access.
- **Auth Required**: Yes
- **Response**: JSON `{ "auth_url": "string" }`

#### Connect Calendar (Callback)
**GET** `/calendar/connect`
- **Description**: OAuth callback endpoint.
- **Query Params**: `code`, `state`

#### Disconnect Calendar
**POST** `/calendar/disconnect`
- **Auth Required**: Yes
- **Response**: JSON Message

#### Sync Calendar
**POST** `/calendar/sync`
- **Description**: Quick sync.
- **Auth Required**: Yes
- **Response**: `CalendarSyncResponse`

#### Full Sync Calendar
**POST** `/calendar/full-sync`
- **Description**: Full sync (longer range).
- **Auth Required**: Yes
- **Response**: `CalendarSyncResponse`

---

## Google Places

#### Autocomplete
**GET** `/places/autocomplete`
- **Query Params**: `query`
- **Auth Required**: Yes
- **Response**: Google Places API result

#### Place Details
**GET** `/places/details`
- **Query Params**: `place_id`
- **Auth Required**: Yes
- **Response**: Google Places API result

#### Map Preview
**GET** `/map-preview`
- **Description**: Returns a static map image for the given coordinates. Proxies through the backend to avoid exposing the Google Maps API key and to work around 403 restrictions on mobile clients.
- **Query Params**: `lat` (required), `lng` (required), `zoom` (optional, 0–21, default 16), `width` (optional, default 640), `height` (optional, default 400)
- **Auth Required**: Yes
- **Response**: Image bytes (`Content-Type: image/png`)

---

## Featured places

Curated venues stored in `featured_places` (e.g. badminton courts). Read-only via this API; ordering is by `name` ascending.

#### List featured places
**GET** `/featured_places`
- **Query Params** (all optional; can be combined):
  - `kind` — filter by `kind` (e.g. `badminton_court`)
  - `tag` — filter rows whose `tags` array contains this string
  - `court_site_key` — exact match on stable scraper key
  - `google_place_id` — exact match on Google Place ID
- **Auth Required**: Yes
- **Response**: Array of `FeaturedPlaceResponse`

#### Get featured place by id
**GET** `/featured_places/{featured_place_id}`
- **Path Params**: `featured_place_id` (UUID)
- **Auth Required**: Yes
- **Response**: `FeaturedPlaceResponse`
- **Errors**: `404` if not found

#### FeaturedPlaceResponse shape
```json
{
  "id": "uuid",
  "name": "string",
  "location": "string | null",
  "address": "string | null",
  "latitude": 0.0,
  "longitude": 0.0,
  "google_place_id": "string | null",
  "preview_image_url": "string | null",
  "tags": ["string"],
  "rating": 0.0,
  "price_level": 0,
  "created_at": "ISO-8601",
  "updated_at": "ISO-8601",
  "kind": "badminton_court",
  "court_site_key": "string | null",
  "extra": {}
}
```

`preview_image_url` matches the role of `SavedIdeaResponse.preview_image_url` (thumbnail for lists and cards). For badminton venues it is typically populated when syncing enrichment from Google Places (Places Photo redirect URL, often `googleusercontent.com`).

---

## System

#### Root
**GET** `/`
- **Welcome message.**

#### Health Check
**GET** `/health`
- **Status check.**

---

## Utilities

#### Proxy Image
**GET** `/api/proxy-image`
- **Description**: Proxy external images (Google avatars, Instagram CDN, YouTube thumbnails) to avoid CORS and rate limits when loading in the Flutter web app. Requires authentication.
- **Query Params**: `url` (required) – the image URL to proxy (must be from an allowed domain)
- **Auth Required**: Yes (Bearer token or `access_token` cookie; cookie enables img src which cannot send headers)
- **Response**: Image bytes (streamed), with `Cache-Control: public, max-age=86400`
- **Allowed domains**: `googleusercontent.com`, `cdninstagram.com`, `fbcdn.net`, `i.ytimg.com`, etc.
- **Example**: `GET /api/proxy-image?url=https%3A%2F%2Flh3.googleusercontent.com%2Fa%2F...`

#### Link Preview
**GET** `/api/preview`
- **Description**: Get metadata preview for a URL (OpenGraph tags, yt-dlp for social media). Optional: the `POST /saved_ideas` endpoint enriches automatically when you provide a URL and omit name/description/preview_image_url. Use this endpoint only if you need to show a preview before saving.
- **Query Params**: `url`
- **Auth Required**: Yes
- **Response**: `LinkPreviewResponse`
  ```json
  {
    "title": "string",
    "description": "string",
    "image": "string",
    "url": "string",
    "domain": "string",
    "site_name": "string",
    "favicon": "string",
    "media_type": "string"
  }
  ```

---

## Guest Endpoints

Guest endpoints allow unauthenticated users to view event details and join via share links. After joining, guests receive a session token to send in the `X-Guest-Token` header for RSVP and chat.

**Path prefix**: `/guest/events/{token}` where `token` is the share link token from the event.

### Get Event (Guest View)
**GET** `/guest/events/{token}`
- **Description**: Fetch event details for a guest view. Returns event info, merged attendee list (invited users + guest participants), and share link status.
- **Auth Required**: No (optional `X-Guest-Token` for session context)
- **Response**: `GuestEventResponse`
  ```json
  {
    "event": {
      "id": "string",
      "title": "string",
      "date_time": "string",
      "end_time": "string | null",
      "location": "string | null",
      "location_address": "string | null",
      "location_lat": "number | null",
      "location_lng": "number | null",
      "notes": "string | null",
      "created_by_name": "string | null",
      "scheduling_poll_closes_at": "string | null",
      "scheduling_poll_mode": "string | null",
      "scheduling_status": "string | null"
    },
    "attendees": [
      {
        "id": "string",
        "name": "string",
        "status": "string",
        "attendee_type": "user | guest"
      }
    ],
    "share_link": { "is_active": true }
  }
  ```
- **Errors**: 404 `share_link_not_found`, `share_link_revoked`, `event_not_found`

### Join Event
**POST** `/guest/events/{token}/join`
- **Description**: Register a guest by name and receive a session token. Inserts into `guest_participants` and adds the guest to the event conversation.
- **Auth Required**: No
- **Request Body**: `GuestJoinRequest`
  ```json
  {
    "name": "string"
  }
  ```
  - `name`: 1–100 characters
- **Response**: `GuestJoinResponse` (201)
  ```json
  {
    "guest_id": "string",
    "session_token": "string",
    "name": "string",
    "event_id": "string"
  }
  ```
- **Errors**: 400 `invalid_name` (empty or >100 chars), 404 `share_link_not_found`, `share_link_revoked`

### Update RSVP
**POST** `/guest/events/{token}/rsvp`
- **Description**: Update a guest's RSVP status (confirmed or declined).
- **Auth Required**: Yes (`X-Guest-Token` header with session token from join)
- **Request Body**: `GuestRsvpRequest`
  ```json
  {
    "status": "confirmed | declined"
  }
  ```
- **Response**: `GuestRsvpResponse`
  ```json
  {
    "status": "string",
    "updated_at": "string"
  }
  ```
- **Errors**: 400 `invalid_status`, 401 `invalid_guest_token`, 404 `share_link_not_found`, `share_link_revoked`

### Get Messages
**GET** `/guest/events/{token}/messages`
- **Description**: Fetch chat messages for the event conversation.
- **Auth Required**: Yes (`X-Guest-Token` header)
- **Query Params**: `limit` (1–100, default 50), `before` (message ID for pagination)
- **Response**: `GuestMessagesResponse`
  ```json
  {
    "messages": [
      {
        "id": "string",
        "sender_name": "string",
        "sender_type": "user | guest",
        "content": "string",
        "created_at": "string",
        "is_mine": false
      }
    ],
    "has_more": false
  }
  ```
- **Errors**: 401 `invalid_guest_token`, 404 `share_link_not_found`, `share_link_revoked`

### Send Message
**POST** `/guest/events/{token}/messages`
- **Description**: Send a chat message as a guest.
- **Auth Required**: Yes (`X-Guest-Token` header)
- **Request Body**: `GuestMessageRequest`
  ```json
  {
    "content": "string"
  }
  ```
  - `content`: 1–2000 characters
- **Response**: `GuestMessageSendResponse` (201)
  ```json
  {
    "id": "string",
    "sender_name": "string",
    "sender_type": "string",
    "content": "string",
    "created_at": "string"
  }
  ```
- **Errors**: 400 `invalid_content`, 401 `invalid_guest_token`, 404 `share_link_not_found`, `share_link_revoked`

### Guest: proposed slots & votes

#### List proposed slots
**GET** `/guest/events/{token}/proposed-slots`
- **Auth Required**: No (valid share link token only)
- **Response**: Same shape as **GET** `/events/{event_id}/proposed-slots` (array of `ProposedSlotListItem`), including the same **default slot** behavior when the poll has no rows yet.

#### Create proposed slot
**POST** `/guest/events/{token}/proposed-slots`
- **Auth Required**: Yes (`X-Guest-Token`)
- **Request Body**: Same as authenticated create (`start_at`, `end_at`, optional `label`, `source`).
- **Response**: `ProposedSlotListItem` (201)

#### Delete proposed slot (guest creator only)
**DELETE** `/guest/events/{token}/proposed-slots/{slot_id}`
- **Auth Required**: Yes (`X-Guest-Token`)
- **Access**: Only the guest who created the slot (hosts use the authenticated DELETE above).

#### Vote / unvote
**POST** `/guest/events/{token}/proposed-slots/{slot_id}/vote` — **DELETE** `/guest/events/{token}/proposed-slots/{slot_id}/vote`
- **Auth Required**: Yes (`X-Guest-Token`)
- **Behavior**: Same `single`-mode rule as authenticated vote when `scheduling_poll_mode` is `single`.

### Guest Error Format
Guest endpoints return errors as JSON:
```json
{
  "error": "error_code",
  "message": "Human-readable message"
}
```
