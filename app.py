import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import uuid
import logging
from supabase import create_client,Client
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# -----------------------------
# PAGE CONFIG
# -----------------------------
st.set_page_config(
    page_title="DevCatalyst Portal",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# -----------------------------
# CONSTANTS & CONFIGURATION
# -----------------------------
ROLE_USERNAMES = {
    "Representatives": ["RajLikhit", "rep2"],
    "Members": ["mem1", "mem2"],
    "Admin": ["admin"]
}

TASK_STATUSES = ['Pending', 'In Progress', 'Submitted', 'Completed']
PRIORITIES = ['High', 'Medium', 'Low']
PRIORITY_ORDER = {'High': 0, 'Medium': 1, 'Low': 2}

# -----------------------------
# SUPABASE CONFIGURATION
# -----------------------------

@st.cache_resource
def init_supabase():
    """Initialize Supabase client with caching."""
    try:
        url = st.secrets["supabase"]["url"]
        key = st.secrets["supabase"]["anon_key"]
        return create_client(url, key)
    except Exception as e:
        logger.error(f"Supabase initialization error: {e}")
        st.error("Database connection failed. Please check configuration.")
        return None

# Get Supabase client
supabase: Client = init_supabase()

# -----------------------------
# UTILITY FUNCTIONS
# -----------------------------

def get_secret_password(role: str, username: str) -> str:
    """Get password from secrets with error handling."""
    try:
        return st.secrets["passwords"][role][username]
    except (KeyError, AttributeError) as e:
        logger.warning(f"Password not found for {role}/{username}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error getting password: {e}")
        return None

def safe_date_parse(date_str):
    """Safely parse date strings."""
    try:
        if isinstance(date_str, str):
            return pd.to_datetime(date_str)
        return pd.to_datetime(date_str) if date_str else None
    except Exception as e:
        logger.warning(f"Date parsing error for '{date_str}': {e}")
        return pd.NaT

def generate_task_id():
    """Generate unique task ID."""
    return f"DC-{uuid.uuid4().hex[:6].upper()}"

def generate_doubt_id():
    """Generate unique doubt ID."""
    return f"DQ-{uuid.uuid4().hex[:6].upper()}"

# -----------------------------
# DATABASE OPERATIONS
# -----------------------------

def save_task_to_db(task_data):
    """Save task to Supabase database."""
    if not supabase:
        return False, "Database not available"
    
    try:
        # Prepare data for database
        db_task = {
            'id': task_data['Task ID'],
            'title': task_data['Task Title'],
            'description': task_data['Description'],
            'priority': task_data['Priority'],
            'status': task_data['Status'],
            'due_date': task_data['Due Date'],
            'assigned_date': task_data['Assigned Date'],
            'points': task_data['Points'],
            'assigned_to': task_data['assigned_to'],
            'verified': task_data.get('verified', False)
        }
        
        # Add submission data if exists
        submission = task_data.get('submission')
        if submission:
            db_task['submission_link'] = submission.get('link')
            db_task['submission_notes'] = submission.get('notes', '')
            db_task['submitted_at'] = submission.get('submitted_at')
        
        result = supabase.table('tasks').insert(db_task).execute()
        return True, result.data
        
    except Exception as e:
        logger.error(f"Save task error: {e}")
        return False, str(e)

def update_task_in_db(task_id, updates):
    """Update task in Supabase database."""
    if not supabase:
        return False, "Database not available"
    
    try:
        result = supabase.table('tasks').update(updates).eq('id', task_id).execute()
        return True, result.data
        
    except Exception as e:
        logger.error(f"Update task error: {e}")
        return False, str(e)

def get_tasks_from_db():
    """Get all tasks from Supabase database."""
    if not supabase:
        return []
    
    try:
        result = supabase.table('tasks').select('*').execute()
        
        # Convert database format back to app format
        tasks = []
        for db_task in result.data:
            task = {
                'Task ID': db_task['id'],
                'Task Title': db_task['title'],
                'Description': db_task['description'],
                'Priority': db_task['priority'],
                'Status': db_task['status'],
                'Due Date': db_task['due_date'],
                'Assigned Date': db_task['assigned_date'],
                'Points': db_task['points'],
                'assigned_to': db_task['assigned_to'],
                'verified': db_task['verified'],
                'created_at': db_task['created_at']
            }
            
            # Add submission data if exists
            if db_task['submission_link']:
                task['submission'] = {
                    'link': db_task['submission_link'],
                    'notes': db_task['submission_notes'] or '',
                    'submitted_at': db_task['submitted_at']
                }
            
            if db_task['verified_at']:
                task['verified_at'] = db_task['verified_at']
            
            tasks.append(task)
        
        return tasks
        
    except Exception as e:
        logger.error(f"Get tasks error: {e}")
        return []

def save_doubt_to_db(doubt_data):
    """Save doubt to Supabase database."""
    if not supabase:
        return False, "Database not available"
    
    try:
        db_doubt = {
            'id': doubt_data['id'],
            'member': doubt_data['member'],
            'title': doubt_data['title'],
            'details': doubt_data['details'],
            'resolved': doubt_data['resolved']
        }
        
        result = supabase.table('doubts').insert(db_doubt).execute()
        return True, result.data
        
    except Exception as e:
        logger.error(f"Save doubt error: {e}")
        return False, str(e)

def save_reply_to_db(doubt_id, rep, message):
    """Save reply to Supabase database."""
    if not supabase:
        return False, "Database not available"
    
    try:
        reply_data = {
            'doubt_id': doubt_id,
            'rep': rep,
            'message': message
        }
        
        result = supabase.table('replies').insert(reply_data).execute()
        return True, result.data
        
    except Exception as e:
        logger.error(f"Save reply error: {e}")
        return False, str(e)

def get_doubts_from_db():
    """Get all doubts with replies from Supabase database."""
    if not supabase:
        return []
    
    try:
        # Get doubts
        doubts_result = supabase.table('doubts').select('*').execute()
        
        # Get replies
        replies_result = supabase.table('replies').select('*').execute()
        
        # Combine doubts with their replies
        doubts = []
        for db_doubt in doubts_result.data:
            doubt = {
                'id': db_doubt['id'],
                'member': db_doubt['member'],
                'title': db_doubt['title'],
                'details': db_doubt['details'],
                'resolved': db_doubt['resolved'],
                'created_at': datetime.fromisoformat(db_doubt['created_at'].replace('Z', '+00:00')),
                'resolved_at': datetime.fromisoformat(db_doubt['resolved_at'].replace('Z', '+00:00')) if db_doubt['resolved_at'] else None,
                'replies': []
            }
            
            # Add replies for this doubt
            doubt_replies = [r for r in replies_result.data if r['doubt_id'] == doubt['id']]
            for reply in doubt_replies:
                doubt['replies'].append({
                    'rep': reply['rep'],
                    'message': reply['message'],
                    'at': datetime.fromisoformat(reply['created_at'].replace('Z', '+00:00'))
                })
            
            # Sort replies by creation time
            doubt['replies'].sort(key=lambda x: x['at'])
            
            doubts.append(doubt)
        
        return doubts
        
    except Exception as e:
        logger.error(f"Get doubts error: {e}")
        return []

def update_doubt_in_db(doubt_id, updates):
    """Update doubt in Supabase database."""
    if not supabase:
        return False, "Database not available"
    
    try:
        result = supabase.table('doubts').update(updates).eq('id', doubt_id).execute()
        return True, result.data
        
    except Exception as e:
        logger.error(f"Update doubt error: {e}")
        return False, str(e)

# -----------------------------
# STATE MANAGEMENT
# -----------------------------

def initialize_app_state():
    """Initialize application state with database sync."""
    if "app_data_loaded" not in st.session_state:
        # Load data from database on first run
        if supabase:
            st.session_state["app_data"] = {
                "tasks": get_tasks_from_db(),
                "doubts": get_doubts_from_db(),
                "profiles": {}
            }
        else:
            # Fallback to session-only storage
            st.session_state["app_data"] = {
                "tasks": [],
                "doubts": [],
                "profiles": {}
            }
        
        st.session_state["app_data_loaded"] = True
    
    # Initialize other session states
    if "member_current_page" not in st.session_state:
        st.session_state["member_current_page"] = "My Tasks"
    
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False

def validate_app_state():
    """Validate app state structure."""
    try:
        data = st.session_state.get("app_data", {})
        
        # Ensure required keys exist
        if "tasks" not in data:
            data["tasks"] = []
        if "doubts" not in data:
            data["doubts"] = []
        if "profiles" not in data:
            data["profiles"] = {}
            
        # Validate task structure
        for task in data["tasks"]:
            if not isinstance(task, dict):
                logger.error(f"Invalid task structure: {task}")
                continue
            
            # Ensure required fields
            required_fields = ['Task ID', 'Task Title', 'Status', 'assigned_to']
            for field in required_fields:
                if field not in task:
                    logger.warning(f"Missing field {field} in task {task.get('Task ID', 'unknown')}")
        
        st.session_state["app_data"] = data
        return True
        
    except Exception as e:
        logger.error(f"State validation error: {e}")
        return False

# -----------------------------
# FLASH MESSAGE SYSTEM
# -----------------------------

def set_flash(message: str, level: str = "success"):
    """Set flash message with validation."""
    if not message:
        return
    
    st.session_state["_flash"] = {
        "message": str(message),
        "level": level if level in ["success", "warning", "error", "info"] else "info"
    }

def render_flash():
    """Render and clear flash messages."""
    flash = st.session_state.get("_flash")
    if not flash:
        return
    
    try:
        level = flash.get("level", "info")
        message = flash.get("message", "")
        
        if not message:
            return
            
        if level == "success":
            st.success(message)
        elif level == "warning":
            st.warning(message)
        elif level == "error":
            st.error(message)
        else:
            st.info(message)
            
    except Exception as e:
        logger.error(f"Flash render error: {e}")
    finally:
        # Always clear flash message
        if "_flash" in st.session_state:
            del st.session_state["_flash"]

# -----------------------------
# TASK MANAGEMENT FUNCTIONS
# -----------------------------

def add_task_for_member(title: str, description: str, priority: str, due_date: str, points: int, assigned_to: str):
    """Add task with database persistence."""
    try:
        # Validation
        if not all([title.strip(), description.strip(), priority, due_date, assigned_to]):
            raise ValueError("All fields are required")
        
        if priority not in PRIORITIES:
            raise ValueError(f"Invalid priority: {priority}")
        
        if points < 1 or points > 100:
            raise ValueError("Points must be between 1 and 100")
        
        if assigned_to not in ROLE_USERNAMES.get("Members", []):
            raise ValueError(f"Invalid member: {assigned_to}")
        
        # Create task
        task = {
            'Task ID': generate_task_id(),
            'Task Title': title.strip(),
            'Description': description.strip(),
            'Priority': priority,
            'Status': 'Pending',
            'Due Date': due_date,
            'Assigned Date': datetime.now().strftime('%Y-%m-%d'),
            'Points': int(points),
            'assigned_to': assigned_to,
            'submission': None,
            'verified': False,
            'created_at': datetime.now().isoformat()
        }
        
        # Save to database
        if supabase:
            success, result = save_task_to_db(task)
            if not success:
                return False, f"Database error: {result}"
        
        # Update session state
        st.session_state["app_data"]["tasks"].append(task)
        
        return True, task['Task ID']
        
    except Exception as e:
        logger.error(f"Add task error: {e}")
        return False, str(e)

def submit_task(task_id: str, link: str, notes: str = ""):
    """Submit task with database persistence."""
    try:
        if not task_id or not link.strip():
            raise ValueError("Task ID and link are required")
        
        # Find task in session state
        task = None
        for t in st.session_state["app_data"]["tasks"]:
            if t.get('Task ID') == task_id:
                task = t
                break
        
        if not task:
            raise ValueError(f"Task {task_id} not found")
        
        if task['Status'] not in ['Pending', 'In Progress']:
            raise ValueError(f"Task {task_id} cannot be submitted (current status: {task['Status']})")
        
        # Update task
        submission_data = {
            "link": link.strip(),
            "notes": notes.strip(),
            "submitted_at": datetime.now().isoformat()
        }
        
        task['submission'] = submission_data
        task['Status'] = 'Submitted'
        
        # Update database
        if supabase:
            updates = {
                'status': 'Submitted',
                'submission_link': link.strip(),
                'submission_notes': notes.strip(),
                'submitted_at': datetime.now().isoformat()
            }
            success, result = update_task_in_db(task_id, updates)
            if not success:
                return False, f"Database error: {result}"
        
        return True, "Task submitted successfully"
        
    except Exception as e:
        logger.error(f"Submit task error: {e}")
        return False, str(e)

def verify_task(task_id: str):
    """Verify task with database persistence."""
    try:
        if not task_id:
            raise ValueError("Task ID is required")
        
        # Find task
        task = None
        for t in st.session_state["app_data"]["tasks"]:
            if t.get('Task ID') == task_id:
                task = t
                break
        
        if not task:
            raise ValueError(f"Task {task_id} not found")
        
        if task['Status'] != 'Submitted':
            raise ValueError(f"Task {task_id} is not in submitted status")
        
        # Update task
        verified_at = datetime.now().isoformat()
        task['verified'] = True
        task['Status'] = 'Completed'
        task['verified_at'] = verified_at
        
        # Update database
        if supabase:
            updates = {
                'verified': True,
                'status': 'Completed',
                'verified_at': verified_at
            }
            success, result = update_task_in_db(task_id, updates)
            if not success:
                return False, f"Database error: {result}"
        
        return True, "Task verified successfully"
        
    except Exception as e:
        logger.error(f"Verify task error: {e}")
        return False, str(e)

def get_user_tasks(username: str):
    """Get tasks for a specific user with error handling."""
    try:
        tasks = st.session_state["app_data"]["tasks"]
        user_tasks = [t for t in tasks if t.get('assigned_to') == username]
        return pd.DataFrame(user_tasks) if user_tasks else pd.DataFrame()
    except Exception as e:
        logger.error(f"Get user tasks error: {e}")
        return pd.DataFrame()

# -----------------------------
# DOUBT MANAGEMENT FUNCTIONS
# -----------------------------

def add_doubt(member: str, title: str, details: str):
    """Add doubt with database persistence."""
    try:
        if not all([member, title.strip(), details.strip()]):
            raise ValueError("All fields are required")
        
        doubt = {
            'id': generate_doubt_id(),
            'member': member,
            'title': title.strip(),
            'details': details.strip(),
            'created_at': datetime.now(),
            'resolved': False,
            'resolved_at': None,
            'replies': []
        }
        
        # Save to database
        if supabase:
            success, result = save_doubt_to_db(doubt)
            if not success:
                return False, f"Database error: {result}"
        
        # Update session state
        st.session_state["app_data"]["doubts"].append(doubt)
        
        return True, doubt['id']
        
    except Exception as e:
        logger.error(f"Add doubt error: {e}")
        return False, str(e)

def reply_to_doubt(doubt_id: str, rep: str, message: str):
    """Reply to doubt with database persistence."""
    try:
        if not all([doubt_id, rep, message.strip()]):
            raise ValueError("All fields are required")
        
        # Find doubt
        doubt = None
        for d in st.session_state["app_data"]["doubts"]:
            if d.get('id') == doubt_id:
                doubt = d
                break
        
        if not doubt:
            raise ValueError(f"Doubt {doubt_id} not found")
        
        # Create reply
        reply = {
            "rep": rep,
            "message": message.strip(),
            "at": datetime.now()
        }
        
        # Save to database
        if supabase:
            success, result = save_reply_to_db(doubt_id, rep, message.strip())
            if not success:
                return False, f"Database error: {result}"
        
        # Update session state
        doubt['replies'].append(reply)
        
        return True, "Reply added successfully"
        
    except Exception as e:
        logger.error(f"Reply to doubt error: {e}")
        return False, str(e)

def mark_doubt_resolved(doubt_id: str):
    """Mark doubt as resolved with database persistence."""
    try:
        if not doubt_id:
            raise ValueError("Doubt ID is required")
        
        # Find doubt
        doubt = None
        for d in st.session_state["app_data"]["doubts"]:
            if d.get('id') == doubt_id:
                doubt = d
                break
        
        if not doubt:
            raise ValueError(f"Doubt {doubt_id} not found")
        
        if doubt['resolved']:
            raise ValueError(f"Doubt {doubt_id} is already resolved")
        
        # Mark as resolved
        resolved_at = datetime.now()
        doubt['resolved'] = True
        doubt['resolved_at'] = resolved_at
        
        # Update database
        if supabase:
            updates = {
                'resolved': True,
                'resolved_at': resolved_at.isoformat()
            }
            success, result = update_doubt_in_db(doubt_id, updates)
            if not success:
                return False, f"Database error: {result}"
        
        return True, "Doubt marked as resolved"
        
    except Exception as e:
        logger.error(f"Mark doubt resolved error: {e}")
        return False, str(e)

# -----------------------------
# UI HELPER FUNCTIONS
# -----------------------------

def get_status_badge(status):
    """Generate status badge HTML."""
    colors = {
        'Pending': {"bg": "#EF4444", "fg": "#FFFFFF"},
        'In Progress': {"bg": "#F59E0B", "fg": "#111827"},
        'Submitted': {"bg": "#F59E0B", "fg": "#111827"},
        'Completed': {"bg": "#10B981", "fg": "#FFFFFF"}
    }
    
    color = colors.get(status, {"bg": "#E5E7EB", "fg": "#111827"})
    return f'''<span style="display:inline-block;padding:4px 10px;border-radius:12px;
              font-size:0.8rem;font-weight:700;background:{color["bg"]};
              color:{color["fg"]};">{status}</span>'''

def get_priority_emoji(priority):
    """Get priority emoji."""
    return {'High': '🔴', 'Medium': '🟡', 'Low': '🟢'}.get(priority, '⚪')

def calculate_days_left(due_date_str):
    """Calculate days left until due date."""
    try:
        due_date = safe_date_parse(due_date_str)
        if pd.isna(due_date):
            return "Invalid date"
        
        days_left = (due_date - pd.Timestamp.now()).days
        
        if days_left < 0:
            return f"Overdue by {abs(days_left)} days"
        elif days_left == 0:
            return "Due Today!"
        else:
            return f"Due in {days_left} days"
            
    except Exception as e:
        logger.error(f"Days left calculation error: {e}")
        return "Date error"

# -----------------------------
# MEMBER PAGES
# -----------------------------

def dashboard(username: str, role: str):
    """Member dashboard with error handling."""
    initialize_app_state()
    validate_app_state()
    
    st.header("⚡ DevCatalyst — Member Dashboard")
    st.caption(f"Logged in as `{username}` (Role: {role})")

    # Get user tasks
    df = get_user_tasks(username)

    st.subheader("Your Progress Overview")

    # Calculate metrics safely
    col1, col2, col3, col4 = st.columns(4)

    total_tasks = len(df) if not df.empty else 0
    completed_tasks = len(df[df['Status'] == 'Completed']) if not df.empty else 0
    pending_tasks = len(df[df['Status'].isin(['Pending', 'In Progress'])]) if not df.empty else 0
    total_points = int(df['Points'].sum()) if not df.empty else 0

    with col1:
        st.metric("Total Tasks", total_tasks)
    with col2:
        st.metric("Completed", completed_tasks)
    with col3:
        st.metric("Pending", pending_tasks)
    with col4:
        st.metric("Total Points", total_points)

    # Progress bar
    completion_rate = (completed_tasks / total_tasks) * 100 if total_tasks > 0 else 0
    st.progress(completion_rate / 100.0, text=f"{completion_rate:.1f}% Complete")

    st.subheader("Your Assigned Tasks")

    # Filters and sorting
    col1, col2 = st.columns([2, 1])
    
    with col1:
        status_options = ["All Tasks"]
        if not df.empty:
            status_options.extend(df['Status'].unique().tolist())
        status_filter = st.selectbox("Filter by Status", status_options)
    
    with col2:
        sort_option = st.selectbox("Sort by", ["Due Date", "Priority", "Points", "Status"])

    # Apply filters
    filtered_df = df.copy()
    if not filtered_df.empty and status_filter != "All Tasks":
        filtered_df = filtered_df[filtered_df['Status'] == status_filter]

    # Apply sorting
    if not filtered_df.empty:
        try:
            if sort_option == "Due Date":
                filtered_df['Due Date'] = filtered_df['Due Date'].apply(safe_date_parse)
                filtered_df = filtered_df.sort_values('Due Date', na_position='last')
            elif sort_option == "Priority":
                filtered_df['priority_order'] = filtered_df['Priority'].map(PRIORITY_ORDER)
                filtered_df = filtered_df.sort_values('priority_order').drop('priority_order', axis=1)
            elif sort_option == "Points":
                filtered_df = filtered_df.sort_values('Points', ascending=False)
            else:  # Status
                filtered_df = filtered_df.sort_values('Status')
        except Exception as e:
            logger.error(f"Sorting error: {e}")
            st.warning("Error sorting tasks. Displaying in default order.")

    # Display tasks
    if filtered_df.empty:
        st.info("No tasks found matching your criteria.")
    else:
        for _, task in filtered_df.iterrows():
            due_text = calculate_days_left(task['Due Date'])
            
            st.markdown(f"**{get_priority_emoji(task['Priority'])} {task['Task Title']}**")
            st.markdown(get_status_badge(task['Status']), unsafe_allow_html=True)
            st.write(task['Description'])
            st.caption(f"Task ID: {task['Task ID']} | Priority: {task['Priority']} | "
                      f"Points: {task['Points']} | Assigned: {task['Assigned Date']} | {due_text}")
            st.divider()

    # Task submission section
    st.subheader("Submit Work")
    
    if df.empty:
        st.info("No tasks assigned yet. Check back later or contact your representative.")
    else:
        # Get submittable tasks
        submittable_statuses = ['Pending', 'In Progress']
        submittable_tasks = df[df['Status'].isin(submittable_statuses)]['Task ID'].tolist()
        
        if not submittable_tasks:
            st.info("No tasks available for submission.")
        else:
            col1, col2 = st.columns([1, 2])
            
            with col1:
                selected_task = st.selectbox("Select Task ID", submittable_tasks)
            
            with col2:
                link = st.text_input("Submission Link (URL)")
                notes = st.text_input("Notes (Optional)")
            
            if st.button("Submit Task"):
                if selected_task and link.strip():
                    success, message = submit_task(selected_task, link, notes)
                    if success:
                        set_flash(f"Task {selected_task} submitted successfully!", "success")
                        st.rerun()
                    else:
                        st.error(f"Submission failed: {message}")
                else:
                    st.warning("Please select a task and provide a submission link.")

def member_help_page(username: str):
    """Member help page with error handling."""
    initialize_app_state()
    validate_app_state()
    
    st.header("Help & Resources")
    st.caption(f"Logged in as `{username}` (Role: Members)")

    # Request form
    st.subheader("Submit a Doubt or Resource Request")
    
    with st.form("doubt_form"):
        title = st.text_input("Brief Title")
        details = st.text_area("Describe your doubt or resource request")
        submitted = st.form_submit_button("Send Request")
        
        if submitted:
            if title.strip() and details.strip():
                success, message = add_doubt(username, title, details)
                if success:
                    set_flash("Your request has been sent. Representatives will respond shortly.", "success")
                    st.rerun()
                else:
                    st.error(f"Failed to send request: {message}")
            else:
                st.warning("Please fill in both title and details.")

    # Display user's doubts
    st.subheader("Your Doubts & Replies")
    
    try:
        my_doubts = [d for d in st.session_state["app_data"]["doubts"] if d.get('member') == username]
        
        if not my_doubts:
            st.info("No doubts submitted yet.")
        else:
            for doubt in sorted(my_doubts, key=lambda x: x.get('created_at', datetime.min), reverse=True):
                status_text = "✅ Resolved" if doubt.get('resolved', False) else "🟡 Open"
                
                with st.expander(f"{status_text} {doubt.get('title', 'Untitled')}"):
                    st.write(doubt.get('details', ''))
                    
                    created_at = doubt.get('created_at')
                    if created_at:
                        st.caption(f"Created: {created_at.strftime('%Y-%m-%d %H:%M')}")
                    
                    replies = doubt.get('replies', [])
                    if replies:
                        st.markdown("**Replies:**")
                        for reply in replies:
                            reply_time = reply.get('at', datetime.now())
                            st.markdown(f"**{reply.get('rep', 'Unknown')}** "
                                      f"({reply_time.strftime('%Y-%m-%d %H:%M')}): "
                                      f"{reply.get('message', '')}")
                    else:
                        st.caption("No replies yet.")
                        
    except Exception as e:
        logger.error(f"Help page error: {e}")
        st.error("Error loading doubts. Please refresh the page.")

# -----------------------------
# REPRESENTATIVE PAGES
# -----------------------------

def rep_tasks_page(rep_username: str):
    """Representative tasks management page."""
    initialize_app_state()
    validate_app_state()
    render_flash()
    
    st.header("Manage Tasks")
    st.caption(f"Logged in as `{rep_username}` (Role: Representatives)")

    # Task assignment form
    st.subheader("Assign New Task")
    
    member_usernames = ROLE_USERNAMES.get("Members", [])
    
    if not member_usernames:
        st.warning("No members available for task assignment.")
    else:
        with st.form("assign_task_form"):
            title = st.text_input("Task Title")
            description = st.text_area("Description")
            
            col1, col2 = st.columns(2)
            with col1:
                priority = st.selectbox("Priority", PRIORITIES)
                points = st.number_input("Points", min_value=1, max_value=100, value=10)
            
            with col2:
                due_date = st.date_input("Due Date", min_value=datetime.now().date())
                assigned_to = st.selectbox("Assign to Member", member_usernames)
            
            submitted = st.form_submit_button("Assign Task")
            
            if submitted:
                success, message = add_task_for_member(
                    title, description, priority, 
                    due_date.strftime('%Y-%m-%d'), points, assigned_to
                )
                
                if success:
                    set_flash(f"Task assigned to {assigned_to} (ID: {message})", "success")
                    st.rerun()
                else:
                    st.error(f"Assignment failed: {message}")

    # Task verification section
    st.subheader("Verify Submissions")
    
    try:
        submitted_tasks = [t for t in st.session_state["app_data"]["tasks"] 
                          if t.get('Status') == 'Submitted']
        
        if not submitted_tasks:
            st.info("No submissions awaiting verification.")
        else:
            for task in submitted_tasks:
                with st.expander(f"{task.get('Task ID', 'Unknown')} - {task.get('Task Title', 'Untitled')} "
                               f"(by {task.get('assigned_to', 'Unknown')})"):
                    
                    st.write(f"**Description:** {task.get('Description', '')}")
                    st.write(f"**Priority:** {task.get('Priority', '')} | "
                           f"**Points:** {task.get('Points', 0)} | "
                           f"**Due:** {task.get('Due Date', '')}")
                    
                    submission = task.get('submission', {})
                    if submission:
                        st.write(f"**Submission Link:** {submission.get('link', 'N/A')}")
                        if submission.get('notes'):
                            st.write(f"**Notes:** {submission.get('notes')}")
                        st.caption(f"Submitted: {submission.get('submitted_at', 'Unknown')}")
                    
                    if st.button("✅ Verify Task", key=f"verify_{task.get('Task ID')}"):
                        success, message = verify_task(task.get('Task ID'))
                        if success:
                            set_flash(f"Task {task.get('Task ID')} verified successfully!", "success")
                            st.rerun()
                        else:
                            st.error(f"Verification failed: {message}")
                            
    except Exception as e:
        logger.error(f"Verification section error: {e}")
        st.error("Error loading submissions. Please refresh the page.")

def rep_doubts_page(rep_username: str):
    """Representative doubts management page."""
    initialize_app_state()
    validate_app_state()
    
    st.header("Member Doubts")
    st.caption(f"Logged in as `{rep_username}` (Role: Representatives)")

    try:
        doubts = st.session_state["app_data"]["doubts"]
        
        if not doubts:
            st.info("No doubts raised by members yet.")
            return

        # Sort doubts: unresolved first, then by creation time
        sorted_doubts = sorted(doubts, key=lambda x: (
            x.get('resolved', False),
            -x.get('created_at', datetime.min).timestamp()
        ))

        for doubt in sorted_doubts:
            status_text = "✅ Resolved" if doubt.get('resolved', False) else "🟡 Open"
            created_time = doubt.get('created_at', datetime.now())
            
            with st.expander(f"{status_text} {doubt.get('title', 'Untitled')} — "
                           f"by {doubt.get('member', 'Unknown')} "
                           f"on {created_time.strftime('%Y-%m-%d %H:%M')}"):
                
                st.write(f"**Details:** {doubt.get('details', '')}")
                
                # Show existing replies
                replies = doubt.get('replies', [])
                if replies:
                    st.markdown("**Previous Replies:**")
                    for reply in replies:
                        reply_time = reply.get('at', datetime.now())
                        st.markdown(f"**{reply.get('rep', 'Unknown')}** "
                                  f"({reply_time.strftime('%Y-%m-%d %H:%M')}): "
                                  f"{reply.get('message', '')}")
                    st.divider()
                
                # Reply form for unresolved doubts
                if not doubt.get('resolved', False):
                    reply_text = st.text_area("Your reply:", key=f"reply_{doubt.get('id')}")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        if st.button("Send Reply", key=f"send_{doubt.get('id')}"):
                            if reply_text.strip():
                                success, message = reply_to_doubt(doubt.get('id'), rep_username, reply_text)
                                if success:
                                    set_flash("Reply sent successfully!", "success")
                                    st.rerun()
                                else:
                                    st.error(f"Failed to send reply: {message}")
                            else:
                                st.warning("Please enter a reply message.")
                    
                    with col2:
                        if st.button("Mark as Resolved", key=f"resolve_{doubt.get('id')}"):
                            success, message = mark_doubt_resolved(doubt.get('id'))
                            if success:
                                set_flash("Doubt marked as resolved!", "success")
                                st.rerun()
                            else:
                                st.error(f"Failed to resolve doubt: {message}")
                else:
                    resolved_time = doubt.get('resolved_at', datetime.now())
                    st.success(f"Resolved on {resolved_time.strftime('%Y-%m-%d %H:%M')}")
                    
    except Exception as e:
        logger.error(f"Doubts page error: {e}")
        st.error("Error loading doubts. Please refresh the page.")

# -----------------------------
# ADMIN PAGES
# -----------------------------

def admin_analytics_page():
    """Admin analytics page."""
    initialize_app_state()
    validate_app_state()
    
    st.header("Analytics Dashboard")
    st.caption("Logged in as `admin` (Role: Admin)")

    try:
        doubts = st.session_state["app_data"]["doubts"]
        tasks = st.session_state["app_data"]["tasks"]

        # Doubts analytics
        st.subheader("📊 Doubts Analytics")
        
        if doubts:
            # Create DataFrame for analysis
            doubt_data = []
            for d in doubts:
                doubt_data.append({
                    'created_date': d.get('created_at', datetime.now()).date(),
                    'resolved_date': d.get('resolved_at').date() if d.get('resolved_at') else None,
                    'resolved': d.get('resolved', False),
                    'replies_count': len(d.get('replies', [])),
                    'member': d.get('member', 'Unknown')
                })
            
            df_doubts = pd.DataFrame(doubt_data)
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Total Doubts", len(doubts))
            with col2:
                resolved_count = sum(1 for d in doubts if d.get('resolved', False))
                st.metric("Resolved Doubts", resolved_count)
            with col3:
                unresolved_count = len(doubts) - resolved_count
                st.metric("Open Doubts", unresolved_count)
                
            # Doubts by member
            if len(df_doubts) > 0:
                doubts_by_member = df_doubts['member'].value_counts()
                st.bar_chart(doubts_by_member)
            
            # Resolution rate
            if len(doubts) > 0:
                resolution_rate = (resolved_count / len(doubts)) * 100
                st.progress(resolution_rate / 100.0, text=f"Resolution Rate: {resolution_rate:.1f}%")
        else:
            st.info("No doubts data available yet.")

        st.divider()

        # Tasks analytics
        st.subheader("📋 Tasks Analytics")
        
        if tasks:
            # Create DataFrame for tasks analysis
            task_data = []
            for t in tasks:
                task_data.append({
                    'assigned_date': safe_date_parse(t.get('Assigned Date', '')).date() if t.get('Assigned Date') else datetime.now().date(),
                    'due_date': safe_date_parse(t.get('Due Date', '')).date() if t.get('Due Date') else None,
                    'status': t.get('Status', 'Unknown'),
                    'priority': t.get('Priority', 'Unknown'),
                    'points': t.get('Points', 0),
                    'assigned_to': t.get('assigned_to', 'Unknown'),
                    'verified': t.get('verified', False)
                })
            
            df_tasks = pd.DataFrame(task_data)
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total Tasks", len(tasks))
            with col2:
                completed_tasks = sum(1 for t in tasks if t.get('Status') == 'Completed')
                st.metric("Completed Tasks", completed_tasks)
            with col3:
                total_points = sum(t.get('Points', 0) for t in tasks)
                st.metric("Total Points", total_points)
            with col4:
                avg_points = total_points / len(tasks) if tasks else 0
                st.metric("Avg Points/Task", f"{avg_points:.1f}")
            
            # Task status distribution
            if len(df_tasks) > 0:
                st.subheader("Task Status Distribution")
                status_counts = df_tasks['status'].value_counts()
                st.bar_chart(status_counts)
                
                # Tasks by member
                st.subheader("Tasks by Member")
                tasks_by_member = df_tasks['assigned_to'].value_counts()
                st.bar_chart(tasks_by_member)
                
                # Priority distribution
                st.subheader("Priority Distribution")
                priority_counts = df_tasks['priority'].value_counts()
                st.bar_chart(priority_counts)
        else:
            st.info("No tasks data available yet.")
            
    except Exception as e:
        logger.error(f"Analytics page error: {e}")
        st.error("Error loading analytics. Please refresh the page.")

def admin_data_page():
    """Admin data management page."""
    initialize_app_state()
    validate_app_state()
    
    st.header("Data Management")
    st.caption("Logged in as `admin` (Role: Admin)")

    # Data export section
    st.subheader("📥 Export Data")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Export Tasks Data"):
            try:
                tasks = st.session_state["app_data"]["tasks"]
                if tasks:
                    df_tasks = pd.DataFrame(tasks)
                    csv_data = df_tasks.to_csv(index=False)
                    st.download_button(
                        label="Download Tasks CSV",
                        data=csv_data,
                        file_name=f"devcatalyst_tasks_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv"
                    )
                else:
                    st.info("No tasks data to export.")
            except Exception as e:
                st.error(f"Export error: {e}")
    
    with col2:
        if st.button("Export Doubts Data"):
            try:
                doubts = st.session_state["app_data"]["doubts"]
                if doubts:
                    # Flatten doubts data for CSV export
                    doubt_records = []
                    for d in doubts:
                        base_record = {
                            'id': d.get('id', ''),
                            'member': d.get('member', ''),
                            'title': d.get('title', ''),
                            'details': d.get('details', ''),
                            'created_at': d.get('created_at', ''),
                            'resolved': d.get('resolved', False),
                            'resolved_at': d.get('resolved_at', ''),
                            'replies_count': len(d.get('replies', []))
                        }
                        doubt_records.append(base_record)
                    
                    df_doubts = pd.DataFrame(doubt_records)
                    csv_data = df_doubts.to_csv(index=False)
                    st.download_button(
                        label="Download Doubts CSV",
                        data=csv_data,
                        file_name=f"devcatalyst_doubts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv"
                    )
                else:
                    st.info("No doubts data to export.")
            except Exception as e:
                st.error(f"Export error: {e}")

    st.divider()

    # Data viewing section
    st.subheader("📊 Raw Data View")
    
    data_view = st.selectbox("Select Data to View", ["Tasks", "Doubts", "System State"])
    
    if data_view == "Tasks":
        tasks = st.session_state["app_data"]["tasks"]
        if tasks:
            df_tasks = pd.DataFrame(tasks)
            st.dataframe(df_tasks, use_container_width=True)
        else:
            st.info("No tasks data available.")
    
    elif data_view == "Doubts":
        doubts = st.session_state["app_data"]["doubts"]
        if doubts:
            # Create a simplified view of doubts
            doubt_display = []
            for d in doubts:
                doubt_display.append({
                    'ID': d.get('id', ''),
                    'Member': d.get('member', ''),
                    'Title': d.get('title', ''),
                    'Created': d.get('created_at', ''),
                    'Resolved': d.get('resolved', False),
                    'Replies': len(d.get('replies', []))
                })
            df_doubts = pd.DataFrame(doubt_display)
            st.dataframe(df_doubts, use_container_width=True)
        else:
            st.info("No doubts data available.")
    
    else:  # System State
        st.json(st.session_state["app_data"])

    st.divider()

    # Data cleanup section
    st.subheader("🧹 Data Cleanup")
    
    st.warning("⚠️ These actions cannot be undone. Use with caution!")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("Clear All Tasks", type="secondary"):
            if st.session_state.get("confirm_clear_tasks", False):
                st.session_state["app_data"]["tasks"] = []
                st.session_state["confirm_clear_tasks"] = False
                set_flash("All tasks cleared successfully!", "warning")
                st.rerun()
            else:
                st.session_state["confirm_clear_tasks"] = True
                st.warning("Click again to confirm clearing all tasks.")
    
    with col2:
        if st.button("Clear All Doubts", type="secondary"):
            if st.session_state.get("confirm_clear_doubts", False):
                st.session_state["app_data"]["doubts"] = []
                st.session_state["confirm_clear_doubts"] = False
                set_flash("All doubts cleared successfully!", "warning")
                st.rerun()
            else:
                st.session_state["confirm_clear_doubts"] = True
                st.warning("Click again to confirm clearing all doubts.")
    
    with col3:
        if st.button("Reset All Data", type="secondary"):
            if st.session_state.get("confirm_reset_all", False):
                st.session_state["app_data"] = {
                    "tasks": [],
                    "doubts": [],
                    "profiles": {}
                }
                st.session_state["confirm_reset_all"] = False
                set_flash("All data reset successfully!", "warning")
                st.rerun()
            else:
                st.session_state["confirm_reset_all"] = True
                st.error("Click again to confirm resetting ALL data.")

# -----------------------------
# AUTHENTICATION SYSTEM
# -----------------------------

def authenticate(username: str, password: str):
    """Authenticate user with role detection."""
    try:
        for role, usernames in ROLE_USERNAMES.items():
            if username in usernames:
                stored_password = get_secret_password(role, username)
                if stored_password and stored_password == password:
                    return True, role
        return False, None
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        return False, None

def login_page():
    """Login page with role-based authentication."""
    st.markdown("""
    <div style="text-align: center; padding: 50px 0;">
        <h1>⚡ DevCatalyst Portal</h1>
        <p style="font-size: 1.2em; color: #666;">Member Task Management System</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Center the login form
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("### Login to Your Account")
        
        with st.form("login_form"):
            username = st.text_input("Username", placeholder="Enter your username")
            password = st.text_input("Password", type="password", placeholder="Enter your password")
            login_button = st.form_submit_button("Login", use_container_width=True)
            
            if login_button:
                if username and password:
                    is_valid, role = authenticate(username, password)
                    if is_valid:
                        st.session_state["logged_in"] = True
                        st.session_state["username"] = username
                        st.session_state["user_role"] = role
                        set_flash(f"Welcome back, {username}!", "success")
                        st.rerun()
                    else:
                        st.error("Invalid username or password.")
                else:
                    st.warning("Please enter both username and password.")

def logout():
    """Logout user and clear session."""
    for key in ["logged_in", "username", "user_role", "member_current_page"]:
        if key in st.session_state:
            del st.session_state[key]
    
    # Clear confirmation states
    for key in list(st.session_state.keys()):
        if key.startswith("confirm_"):
            del st.session_state[key]
    
    set_flash("You have been logged out successfully.", "info")
    st.rerun()

# -----------------------------
# NAVIGATION SYSTEM
# -----------------------------

def create_sidebar(username: str, role: str):
    """Create role-based sidebar navigation."""
    with st.sidebar:
        st.markdown(f"### Welcome, {username}")
        st.caption(f"Role: {role}")
        
        st.divider()
        
        if role == "Members":
            # Member navigation
            pages = ["My Tasks", "Help & Resources"]
            
            # Custom styling for selected page
            current_page = st.session_state.get("member_current_page", "My Tasks")
            
            for page in pages:
                if st.button(
                    page, 
                    key=f"nav_{page}",
                    use_container_width=True,
                    type="primary" if current_page == page else "secondary"
                ):
                    st.session_state["member_current_page"] = page
                    st.rerun()
            
        elif role == "Representatives":
            # Representative navigation
            if st.button("Manage Tasks", use_container_width=True):
                st.session_state["rep_current_page"] = "tasks"
                st.rerun()
            
            if st.button("Member Doubts", use_container_width=True):
                st.session_state["rep_current_page"] = "doubts"
                st.rerun()
        
        elif role == "Admin":
            # Admin navigation
            if st.button("Analytics", use_container_width=True):
                st.session_state["admin_current_page"] = "analytics"
                st.rerun()
            
            if st.button("Data Management", use_container_width=True):
                st.session_state["admin_current_page"] = "data"
                st.rerun()
        
        st.divider()
        
        # Logout button
        if st.button("🚪 Logout", use_container_width=True, type="secondary"):
            logout()

# -----------------------------
# MAIN APPLICATION
# -----------------------------

def main():
    """Main application entry point."""
    # Apply custom CSS
    st.markdown("""
    <style>
    .main-header {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        margin-bottom: 2rem;
    }
    
    .metric-card {
        background: #f8fafc;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #3b82f6;
    }
    
    .status-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 9999px;
        font-size: 0.875rem;
        font-weight: 500;
    }
    
    .stButton > button {
        border-radius: 8px;
    }
    
    .stSelectbox > div > div {
        border-radius: 8px;
    }
    </style>
    """, unsafe_allow_html=True)
    
    initialize_app_state()
    
    # Render flash messages
    render_flash()
    
    # Check authentication
    if not st.session_state.get("logged_in", False):
        login_page()
        return
    
    username = st.session_state.get("username", "")
    role = st.session_state.get("user_role", "")
    
    if not username or not role:
        st.error("Session error. Please login again.")
        logout()
        return
    
    # Create sidebar navigation
    create_sidebar(username, role)
    
    # Route to appropriate page based on role
    try:
        if role == "Members":
            current_page = st.session_state.get("member_current_page", "My Tasks")
            
            if current_page == "My Tasks":
                dashboard(username, role)
            elif current_page == "Help & Resources":
                member_help_page(username)
        
        elif role == "Representatives":
            current_page = st.session_state.get("rep_current_page", "tasks")
            
            if current_page == "tasks":
                rep_tasks_page(username)
            elif current_page == "doubts":
                rep_doubts_page(username)
        
        elif role == "Admin":
            current_page = st.session_state.get("admin_current_page", "analytics")
            
            if current_page == "analytics":
                admin_analytics_page()
            elif current_page == "data":
                admin_data_page()
        
        else:
            st.error(f"Unknown role: {role}")
            logout()
            
    except Exception as e:
        logger.error(f"Page routing error: {e}")
        st.error("An error occurred while loading the page. Please refresh and try again.")

# -----------------------------
# APPLICATION ENTRY POINT
# -----------------------------

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.critical(f"Critical application error: {e}")
        st.error("A critical error occurred. Please contact support.")
        st.code(f"Error: {e}")
