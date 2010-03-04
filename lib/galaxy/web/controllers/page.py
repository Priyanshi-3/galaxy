from galaxy.web.base.controller import *
from galaxy.web.framework.helpers import time_ago, grids
from galaxy.util.sanitize_html import sanitize_html, _BaseHTMLProcessor
from galaxy.util.odict import odict
from galaxy.util.json import from_json_string

import re

VALID_SLUG_RE = re.compile( "^[a-z0-9\-]+$" )

def format_bool( b ):
    if b:
        return "yes"
    else:
        return ""

class PageListGrid( grids.Grid ):
    # Custom column.
    class URLColumn( grids.PublicURLColumn ):
        def get_value( self, trans, grid, item ):
            return url_for( action='display_by_username_and_slug', username=item.user.username, slug=item.slug )
    
    # Grid definition
    use_panels = True
    title = "Pages"
    model_class = model.Page
    default_filter = { "published" : "All", "tags" : "All", "title" : "All", "sharing" : "All" }
    default_sort_key = "-create_time"
    columns = [
        grids.TextColumn( "Title", key="title", model_class=model.Page, attach_popup=True, filterable="advanced" ),
        URLColumn( "Public URL" ),
        grids.IndividualTagsColumn( "Tags", "tags", model.Page, model.PageTagAssociation, filterable="advanced", grid_name="PageListGrid" ),
        grids.SharingStatusColumn( "Sharing", key="sharing", model_class=model.Page, filterable="advanced", sortable=False ),
        grids.GridColumn( "Created", key="create_time", format=time_ago ),
        grids.GridColumn( "Last Updated", key="update_time", format=time_ago ),
    ]
    columns.append( 
        grids.MulticolFilterColumn(  
        "Search", 
        cols_to_filter=[ columns[0], columns[2] ], 
        key="free-text-search", visible=False, filterable="standard" )
                )
    global_actions = [
        grids.GridAction( "Add new page", dict( action='create' ) )
    ]
    operations = [
        grids.DisplayByUsernameAndSlugGridOperation( "View", allow_multiple=False ),
        grids.GridOperation( "Edit attributes", allow_multiple=False, url_args=dict( action='edit') ),
        grids.GridOperation( "Edit content", allow_multiple=False, url_args=dict( action='edit_content') ),
        grids.GridOperation( "Share or Publish", allow_multiple=False, condition=( lambda item: not item.deleted ), async_compatible=False ),
        grids.GridOperation( "Delete" ),
    ]
    def apply_default_filter( self, trans, query, **kwargs ):
        return query.filter_by( user=trans.user, deleted=False )
        
class PageAllPublishedGrid( grids.Grid ):
    # Grid definition
    use_panels = True
    use_async = True
    title = "Published Pages"
    model_class = model.Page
    default_sort_key = "-update_time"
    default_filter = dict( title="All", username="All" )
    columns = [
        grids.PublicURLColumn( "Title", key="title", model_class=model.Page, filterable="advanced"),
        grids.OwnerAnnotationColumn( "Annotation", key="annotation", model_class=model.Page, model_annotation_association_class=model.PageAnnotationAssociation, filterable="advanced" ),
        grids.OwnerColumn( "Owner", key="username", model_class=model.User, filterable="advanced", sortable=False ), 
        grids.CommunityTagsColumn( "Community Tags", "tags", model.Page, model.PageTagAssociation, filterable="advanced", grid_name="PageAllPublishedGrid" ),
        grids.GridColumn( "Last Updated", key="update_time", format=time_ago )
    ]
    columns.append( 
        grids.MulticolFilterColumn(  
        "Search", 
        cols_to_filter=[ columns[0], columns[1], columns[2], columns[3] ], 
        key="free-text-search", visible=False, filterable="standard" )
                )
    def build_initial_query( self, session ):
        # Join so that searching history.user makes sense.
        return session.query( self.model_class ).join( model.User.table )
    def apply_default_filter( self, trans, query, **kwargs ):
        return query.filter( self.model_class.deleted==False ).filter( self.model_class.published==True )
                
class ItemSelectionGrid( grids.Grid ):
    """ Base class for pages' item selection grids. """
    # Custom columns.
    class NameColumn( grids.TextColumn ):
        def get_value(self, trans, grid, item):
            if hasattr( item, "get_display_name" ):
                return item.get_display_name()
            else:
                return item.name

    # Grid definition.
    template = "/page/select_items_grid.mako"
    async_template = "/page/select_items_grid_async.mako" 
    default_filter = { "deleted" : "False" , "sharing" : "All" }
    default_sort_key = "-update_time"
    use_async = True
    use_paging = True
    num_rows_per_page = 10
    
    def apply_default_filter( self, trans, query, **kwargs ):
        return query.filter_by( user=trans.user )
                
class HistorySelectionGrid( ItemSelectionGrid ):
    """ Grid for selecting histories. """
    # Grid definition.
    title = "Saved Histories"
    model_class = model.History
    columns = [
        ItemSelectionGrid.NameColumn( "Name", key="name", model_class=model.History, filterable="advanced" ),
        grids.IndividualTagsColumn( "Tags", "tags", model.History, model.HistoryTagAssociation, filterable="advanced"),
        grids.GridColumn( "Last Updated", key="update_time", format=time_ago ),
        # Columns that are valid for filtering but are not visible.
        grids.DeletedColumn( "Deleted", key="deleted", visible=False, filterable="advanced" ),
        grids.SharingStatusColumn( "Sharing", key="sharing", model_class=model.History, filterable="advanced", sortable=False, visible=False ),
    ]
    columns.append(     
        grids.MulticolFilterColumn(  
        "Search", 
        cols_to_filter=[ columns[0], columns[1] ], 
        key="free-text-search", visible=False, filterable="standard" )
                )
                
    def apply_default_filter( self, trans, query, **kwargs ):
        return query.filter_by( user=trans.user, purged=False )
        
class HistoryDatasetAssociationSelectionGrid( ItemSelectionGrid ):
    """ Grid for selecting HDAs. """
    # Grid definition.
    title = "Saved Datasets"
    model_class = model.HistoryDatasetAssociation
    columns = [
        ItemSelectionGrid.NameColumn( "Name", key="name", model_class=model.HistoryDatasetAssociation, filterable="advanced" ),
        grids.IndividualTagsColumn( "Tags", "tags", model.StoredWorkflow, model.HistoryDatasetAssociationTagAssociation, filterable="advanced"),
        grids.GridColumn( "Last Updated", key="update_time", format=time_ago ),
        # Columns that are valid for filtering but are not visible.
        grids.DeletedColumn( "Deleted", key="deleted", visible=False, filterable="advanced" ),
        grids.SharingStatusColumn( "Sharing", key="sharing", model_class=model.HistoryDatasetAssociation, filterable="advanced", sortable=False, visible=False ),
    ]
    columns.append(     
        grids.MulticolFilterColumn(  
        "Search", 
        cols_to_filter=[ columns[0], columns[1] ], 
        key="free-text-search", visible=False, filterable="standard" )
                )
    def apply_default_filter( self, trans, query, **kwargs ):
        # To filter HDAs by user, need to join HDA and History table and then filter histories by user. This is necessary because HDAs do not have
        # a user relation.
        return query.select_from( model.HistoryDatasetAssociation.table.join( model.History.table ) ).filter( model.History.user == trans.user )
    
                
class WorkflowSelectionGrid( ItemSelectionGrid ):
    """ Grid for selecting workflows. """
    # Grid definition.
    title = "Saved Workflows"
    model_class = model.StoredWorkflow
    columns = [
        ItemSelectionGrid.NameColumn( "Name", key="name", model_class=model.StoredWorkflow, filterable="advanced" ),
        grids.IndividualTagsColumn( "Tags", "tags", model.StoredWorkflow, model.StoredWorkflowTagAssociation, filterable="advanced"),
        grids.GridColumn( "Last Updated", key="update_time", format=time_ago ),
        # Columns that are valid for filtering but are not visible.
        grids.DeletedColumn( "Deleted", key="deleted", visible=False, filterable="advanced" ),
        grids.SharingStatusColumn( "Sharing", key="sharing", model_class=model.StoredWorkflow, filterable="advanced", sortable=False, visible=False ),
    ]
    columns.append(     
        grids.MulticolFilterColumn(  
        "Search", 
        cols_to_filter=[ columns[0], columns[1] ], 
        key="free-text-search", visible=False, filterable="standard" )
                )

class PageSelectionGrid( ItemSelectionGrid ):
    """ Grid for selecting pages. """
    # Grid definition.
    title = "Saved Pages"
    model_class = model.Page
    columns = [
        grids.TextColumn( "Title", key="title", model_class=model.Page, filterable="advanced" ),
        grids.IndividualTagsColumn( "Tags", "tags", model.Page, model.PageTagAssociation, filterable="advanced"),
        grids.GridColumn( "Last Updated", key="update_time", format=time_ago ),
        # Columns that are valid for filtering but are not visible.
        grids.DeletedColumn( "Deleted", key="deleted", visible=False, filterable="advanced" ),
        grids.SharingStatusColumn( "Sharing", key="sharing", model_class=model.Page, filterable="advanced", sortable=False, visible=False ),
    ]
    columns.append(     
        grids.MulticolFilterColumn(  
        "Search",
        cols_to_filter=[ columns[0], columns[1] ], 
        key="free-text-search", visible=False, filterable="standard" )
                )
                
class _PageContentProcessor( _BaseHTMLProcessor ):
    """ Processes page content to produce HTML that is suitable for display. For now, processor renders embedded objects. """
    
    def __init__( self, trans, encoding, type, render_embed_html_fn ):
        _BaseHTMLProcessor.__init__( self, encoding, type)
        self.trans = trans
        self.ignore_content = False
        self.num_open_tags_for_ignore = 0
        self.render_embed_html_fn = render_embed_html_fn
        
    def unknown_starttag( self, tag, attrs ):
        """ Called for each start tag; attrs is a list of (attr, value) tuples. """
    
        # If ignoring content, just increment tag count and ignore.
        if self.ignore_content:
            self.num_open_tags_for_ignore += 1
            return
        
        # Not ignoring tag; look for embedded content.
        embedded_item = False
        for attribute in attrs:
            if ( attribute[0] == "class" ) and ( "embedded-item" in attribute[1].split(" ") ): 
                embedded_item = True
                break
        # For embedded content, set ignore flag to ignore current content and add new content for embedded item.
        if embedded_item:
            # Set processing attributes to ignore content.
            self.ignore_content = True
            self.num_open_tags_for_ignore = 1
            
            # Insert content for embedded element.
            for attribute in attrs:
                name = attribute[0]
                if name == "id":
                    # ID has form '<class_name>-<encoded_item_id>'
                    item_class, item_id = attribute[1].split("-")
                    embed_html = self.render_embed_html_fn( self.trans, item_class, item_id )
                    self.pieces.append( embed_html )
            return
        
        # Default behavior: not ignoring and no embedded content.
        _BaseHTMLProcessor.unknown_starttag( self, tag, attrs )
        
    def handle_data( self, text ):
        """ Called for each block of plain text. """
        if self.ignore_content:
            return
        _BaseHTMLProcessor.handle_data( self, text )
        
    def unknown_endtag( self, tag ):
        """ Called for each end tag. """
        
        # If ignoring content, see if current tag is the end of content to ignore.
        if self.ignore_content:
            self.num_open_tags_for_ignore -= 1        
            if self.num_open_tags_for_ignore == 0:
                # Done ignoring content.
                self.ignore_content = False
            return
        
        # Default behavior: 
        _BaseHTMLProcessor.unknown_endtag( self, tag )
                
class PageController( BaseController, Sharable, UsesAnnotations, UsesHistory, UsesStoredWorkflow, UsesHistoryDatasetAssociation ):
    
    _page_list = PageListGrid()
    _all_published_list = PageAllPublishedGrid()
    _history_selection_grid = HistorySelectionGrid()
    _workflow_selection_grid = WorkflowSelectionGrid()
    _datasets_selection_grid = HistoryDatasetAssociationSelectionGrid()
    _page_selection_grid = PageSelectionGrid()
    
    @web.expose
    @web.require_login()  
    def list( self, trans, *args, **kwargs ):
        """ List user's pages. """
        # Handle operation
        if 'operation' in kwargs and 'id' in kwargs:
            session = trans.sa_session
            operation = kwargs['operation'].lower()
            ids = util.listify( kwargs['id'] )
            for id in ids:
                item = session.query( model.Page ).get( trans.security.decode_id( id ) )
                if operation == "delete":
                    item.deleted = True
                if operation == "share or publish":
                    return self.sharing( trans, **kwargs )
            session.flush()
            
        # Build grid
        grid = self._page_list( trans, *args, **kwargs )
        
        # Build list of pages shared with user.
        shared_by_others = trans.sa_session \
            .query( model.PageUserShareAssociation ) \
            .filter_by( user=trans.get_user() ) \
            .join( model.Page.table ) \
            .filter( model.Page.deleted == False ) \
            .order_by( desc( model.Page.update_time ) ) \
            .all()
        
        # Render grid wrapped in panels
        return trans.fill_template( "page/index.mako", grid=grid, shared_by_others=shared_by_others )
             
    @web.expose
    def list_published( self, trans, *args, **kwargs ):
        grid = self._all_published_list( trans, *args, **kwargs )
        if 'async' in kwargs:
            return grid
        else:
            # Render grid wrapped in panels
            return trans.fill_template( "page/list_published.mako", grid=grid )

             
    @web.expose
    @web.require_login( "create pages" )
    def create( self, trans, page_title="", page_slug="", page_annotation="" ):
        """
        Create a new page
        """
        user = trans.get_user()
        page_title_err = page_slug_err = page_annotation_err = ""
        if trans.request.method == "POST":
            if not page_title:
                page_title_err = "Page name is required"
            elif not page_slug:
                page_slug_err = "Page id is required"
            elif not VALID_SLUG_RE.match( page_slug ):
                page_slug_err = "Page identifier must consist of only lowercase letters, numbers, and the '-' character"
            elif trans.sa_session.query( model.Page ).filter_by( user=user, slug=page_slug, deleted=False ).first():
                page_slug_err = "Page id must be unique"
            else:
                # Create the new stored page
                page = model.Page()
                page.title = page_title
                page.slug = page_slug
                page_annotation = sanitize_html( page_annotation, 'utf-8', 'text/html' )
                self.add_item_annotation( trans, page, page_annotation )
                page.user = user
                # And the first (empty) page revision
                page_revision = model.PageRevision()
                page_revision.title = page_title
                page_revision.page = page
                page.latest_revision = page_revision
                page_revision.content = ""
                # Persist
                session = trans.sa_session
                session.add( page )
                session.flush()
                # Display the management page
                ## trans.set_message( "Page '%s' created" % page.title )
                return trans.response.send_redirect( web.url_for( action='list' ) )
        return trans.show_form( 
            web.FormBuilder( web.url_for(), "Create new page", submit_text="Submit" )
                .add_text( "page_title", "Page title", value=page_title, error=page_title_err )
                .add_text( "page_slug", "Page identifier", value=page_slug, error=page_slug_err,
                           help="""A unique identifier that will be used for
                                public links to this page. A default is generated
                                from the page title, but can be edited. This field
                                must contain only lowercase letters, numbers, and
                                the '-' character.""" )
                .add_text( "page_annotation", "Page annotation", value=page_annotation, error=page_annotation_err,
                            help="A description of the page; annotation is shown alongside published pages."),
                template="page/create.mako" )
        
    @web.expose
    @web.require_login( "create pages" )
    def edit( self, trans, id, page_title="", page_slug="", page_annotation="" ):
        """
        Create a new page
        """
        encoded_id = id
        id = trans.security.decode_id( id )
        session = trans.sa_session
        page = session.query( model.Page ).get( id )
        user = trans.user
        assert page.user == user
        page_title_err = page_slug_err = page_annotation_err = ""
        if trans.request.method == "POST":
            if not page_title:
                page_title_err = "Page name is required"
            elif not page_slug:
                page_slug_err = "Page id is required"
            elif not VALID_SLUG_RE.match( page_slug ):
                page_slug_err = "Page identifier must consist of only lowercase letters, numbers, and the '-' character"
            elif page_slug != page.slug and trans.sa_session.query( model.Page ).filter_by( user=user, slug=page_slug, deleted=False ).first():
                page_slug_err = "Page id must be unique"
            elif not page_annotation:
                page_annotation_err = "Page annotation is required"
            else:
                page.title = page_title
                page.slug = page_slug
                page_annotation = sanitize_html( page_annotation, 'utf-8', 'text/html' )
                self.add_item_annotation( trans, page, page_annotation )
                session.flush()
                # Redirect to page list.
                return trans.response.send_redirect( web.url_for( action='list' ) )
        else:
            page_title = page.title
            page_slug = page.slug
            page_annotation = self.get_item_annotation_str( trans.sa_session, trans.get_user(), page )
            if not page_annotation:
                page_annotation = ""
        return trans.show_form( 
            web.FormBuilder( web.url_for( id=encoded_id ), "Edit page attributes", submit_text="Submit" )
                .add_text( "page_title", "Page title", value=page_title, error=page_title_err )
                .add_text( "page_slug", "Page identifier", value=page_slug, error=page_slug_err,
                           help="""A unique identifier that will be used for
                                public links to this page. A default is generated
                                from the page title, but can be edited. This field
                                must contain only lowercase letters, numbers, and
                                the '-' character.""" )
                .add_text( "page_annotation", "Page annotation", value=page_annotation, error=page_annotation_err,
                            help="A description of the page; annotation is shown alongside published pages."),
            template="page/create.mako" )
        
    @web.expose
    @web.require_login( "edit pages" )
    def edit_content( self, trans, id ):
        """
        Render the main page editor interface. 
        """
        id = trans.security.decode_id( id )
        page = trans.sa_session.query( model.Page ).get( id )
        assert page.user == trans.user
        return trans.fill_template( "page/editor.mako", page=page )
        
    @web.expose
    @web.require_login( "use Galaxy pages" )
    def sharing( self, trans, id, **kwargs ):
        """ Handle page sharing. """

        # Get session and page.
        session = trans.sa_session
        page = trans.sa_session.query( model.Page ).get( trans.security.decode_id( id ) )

        # Do operation on page.
        if 'make_accessible_via_link' in kwargs:
            self._make_item_accessible( trans.sa_session, page )
        elif 'make_accessible_and_publish' in kwargs:
            self._make_item_accessible( trans.sa_session, page )
            page.published = True
        elif 'publish' in kwargs:
            page.published = True
        elif 'disable_link_access' in kwargs:
            page.importable = False
        elif 'unpublish' in kwargs:
            page.published = False
        elif 'disable_link_access_and_unpublish' in kwargs:
            page.importable = page.published = False
        elif 'unshare_user' in kwargs:
            user = session.query( model.User ).get( trans.security.decode_id( kwargs['unshare_user' ] ) )
            if not user:
                error( "User not found for provided id" )
            association = session.query( model.PageUserShareAssociation ) \
                                 .filter_by( user=user, page=page ).one()
            session.delete( association )

        session.flush()

        return trans.fill_template( "/sharing_base.mako",
                                    item=page )
                                    
    @web.expose
    @web.require_login( "use Galaxy pages" )
    def share( self, trans, id, email="" ):
        msg = mtype = None
        page = trans.sa_session.query( model.Page ).get( trans.security.decode_id( id ) )
        if email:
            other = trans.sa_session.query( model.User ) \
                                    .filter( and_( model.User.table.c.email==email,
                                                   model.User.table.c.deleted==False ) ) \
                                    .first()
            if not other:
                mtype = "error"
                msg = ( "User '%s' does not exist" % email )
            elif other == trans.get_user():
                mtype = "error"
                msg = ( "You cannot share a workflow with yourself" )
            elif trans.sa_session.query( model.PageUserShareAssociation ) \
                    .filter_by( user=other, page=page ).count() > 0:
                mtype = "error"
                msg = ( "Workflow already shared with '%s'" % email )
            else:
                share = model.PageUserShareAssociation()
                share.page = page
                share.user = other
                session = trans.sa_session
                session.add( share )
                self.set_item_slug( session, page )
                session.flush()
                trans.set_message( "Page '%s' shared with user '%s'" % ( page.title, other.email ) )
                return trans.response.send_redirect( url_for( controller='page', action='sharing', id=id ) )
        return trans.fill_template( "/share_base.mako",
                                    message = msg,
                                    messagetype = mtype,
                                    item=page,
                                    email=email )
        
    @web.expose
    @web.require_login() 
    def save( self, trans, id, content, annotations ):
        id = trans.security.decode_id( id )
        page = trans.sa_session.query( model.Page ).get( id )
        assert page.user == trans.user
        
        # Sanitize content
        content = sanitize_html( content, 'utf-8', 'text/html' )
        
        # Add a new revision to the page with the provided content.
        page_revision = model.PageRevision()
        page_revision.title = page.title
        page_revision.page = page
        page.latest_revision = page_revision
        page_revision.content = content
        
        # Save annotations.
        annotations = from_json_string( annotations )
        for annotation_dict in annotations:
            item_id = trans.security.decode_id( annotation_dict[ 'item_id' ] )
            item_class = self.get_class( annotation_dict[ 'item_class' ] )
            item = trans.sa_session.query( item_class ).filter_by( id=item_id ).first()
            if not item:
                raise RuntimeError( "cannot find annotated item" )
            text = sanitize_html( annotation_dict[ 'text' ], 'utf-8', 'text/html' )
            
            # Add/update annotation.
            if item_id and item_class and text:
                # Get annotation association.
                annotation_assoc_class = eval( "model.%sAnnotationAssociation" % item_class.__name__ )
                annotation_assoc = trans.sa_session.query( annotation_assoc_class ).filter_by( user=trans.get_user() )
                if item_class == model.History.__class__:
                    annotation_assoc = annotation_assoc.filter_by( history=item )
                elif item_class == model.HistoryDatasetAssociation.__class__:
                    annotation_assoc = annotation_assoc.filter_by( hda=item )
                elif item_class == model.StoredWorkflow.__class__:
                    annotation_assoc = annotation_assoc.filter_by( stored_workflow=item )
                elif item_class == model.WorkflowStep.__class__:
                    annotation_assoc = annotation_assoc.filter_by( workflow_step=item )
                annotation_assoc = annotation_assoc.first()
                if not annotation_assoc:
                    # Create association.
                    annotation_assoc = annotation_assoc_class()
                    item.annotations.append( annotation_assoc )
                    annotation_assoc.user = trans.get_user()
                # Set annotation user text.
                annotation_assoc.annotation = text
        trans.sa_session.flush()
        
    @web.expose
    @web.require_login()  
    def display( self, trans, id ):
        id = trans.security.decode_id( id )
        page = trans.sa_session.query( model.Page ).get( id )
        if not page:
            raise web.httpexceptions.HTTPNotFound()
        return self.display_by_username_and_slug( trans, page.user.username, page.slug )

    @web.expose
    def display_by_username_and_slug( self, trans, username, slug ):
        """ Display page based on a username and slug. """ 

        # Get page.
        session = trans.sa_session
        user = session.query( model.User ).filter_by( username=username ).first()
        page = trans.sa_session.query( model.Page ).filter_by( user=user, slug=slug, deleted=False ).first()
        if page is None:
            raise web.httpexceptions.HTTPNotFound()
        # Security check raises error if user cannot access page.
        self.security_check( trans.get_user(), page, False, True)
            
        # Process page content.
        processor = _PageContentProcessor( trans, 'utf-8', 'text/html', self._get_embed_html )
        processor.feed( page.latest_revision.content )
        # Output is string, so convert to unicode for display.
        page_content = unicode( processor.output(), 'utf-8' )
        return trans.fill_template_mako( "page/display.mako", item=page, item_data=page_content, content_only=True )
        
    @web.expose
    @web.require_login( "use Galaxy pages" )
    def set_accessible_async( self, trans, id=None, accessible=False ):
        """ Set page's importable attribute and slug. """
        page = self.get_page( trans, id )

        # Only set if importable value would change; this prevents a change in the update_time unless attribute really changed.
        importable = accessible in ['True', 'true', 't', 'T'];
        if page.importable != importable:
            if importable:
                self._make_item_accessible( trans.sa_session, page )
            else:
                page.importable = importable
            trans.sa_session.flush()
        return

    @web.expose
    @web.require_login( "modify Galaxy items" )
    def set_slug_async( self, trans, id, new_slug ):
        page = self.get_page( trans, id )
        if page:
            page.slug = new_slug
            trans.sa_session.flush()
            return page.slug
            
    @web.expose
    def get_embed_html_async( self, trans, id ):
        """ Returns HTML for embedding a workflow in a page. """

        # TODO: user should be able to embed any item he has access to. see display_by_username_and_slug for security code.
        page = self.get_page( trans, id )
        if page:
            return "Embedded Page '%s'" % page.title

    @web.expose
    @web.json
    @web.require_login( "use Galaxy pages" )
    def get_name_and_link_async( self, trans, id=None ):
        """ Returns page's name and link. """
        page = self.get_page( trans, id )

        if self.set_item_slug( trans.sa_session, page ):
            trans.sa_session.flush()
        return_dict = { "name" : page.title, "link" : url_for( action="display_by_username_and_slug", username=page.user.username, slug=page.slug ) }
        return return_dict
        
    @web.expose
    @web.require_login("select a history from saved histories")
    def list_histories_for_selection( self, trans, **kwargs ):
        """ Returns HTML that enables a user to select one or more histories. """
        # Render the list view
        return self._history_selection_grid( trans, **kwargs )
        
    @web.expose
    @web.require_login("select a workflow from saved workflows")
    def list_workflows_for_selection( self, trans, **kwargs ):
        """ Returns HTML that enables a user to select one or more workflows. """
        # Render the list view
        return self._workflow_selection_grid( trans, **kwargs )
        
    @web.expose
    @web.require_login("select a page from saved pages")
    def list_pages_for_selection( self, trans, **kwargs ):
        """ Returns HTML that enables a user to select one or more pages. """
        # Render the list view
        return self._page_selection_grid( trans, **kwargs )
        
    @web.expose
    @web.require_login("select a dataset from saved datasets")
    def list_datasets_for_selection( self, trans, **kwargs ):
        """ Returns HTML that enables a user to select one or more datasets. """
        # Render the list view
        return self._datasets_selection_grid( trans, **kwargs )
        
    @web.expose
    @web.require_login("get annotation table for history")
    def get_history_annotation_table( self, trans, id ):
        """ Returns HTML for an annotation table for a history. """
        history = self.get_history( trans, id, False, True )
        
        if history:
            datasets = self.get_history_datasets( trans, history )
            return trans.fill_template( "page/history_annotation_table.mako", history=history, datasets=datasets, show_deleted=False )
            
    @web.expose
    def get_editor_iframe( self, trans ):
        """ Returns the document for the page editor's iframe. """
        return trans.fill_template( "page/wymiframe.mako" )
        
    def get_page( self, trans, id, check_ownership=True, check_accessible=False ):
        """Get a page from the database by id, verifying ownership."""
        # Load history from database
        id = trans.security.decode_id( id )
        page = trans.sa_session.query( model.Page ).get( id )
        if not page:
            err+msg( "Page not found" )
        else:
            return self.security_check( trans.get_user(), page, check_ownership, check_accessible )
        
    def _get_embed_html( self, trans, item_class, item_id ):
        """ Returns HTML for embedding an item in a page. """
        item_class = self.get_class( item_class )
        if item_class == model.History:
            history = self.get_history( trans, item_id, False, True )
            history.annotation = self.get_item_annotation_str( trans.sa_session, history.user, history )
            if history:
                datasets = self.get_history_datasets( trans, history )
                return trans.fill_template( "history/embed.mako", item=history, item_data=datasets )
        elif item_class == model.HistoryDatasetAssociation:
            dataset = self.get_dataset( trans, item_id )
            dataset.annotation = self.get_item_annotation_str( trans.sa_session, dataset.history.user, dataset )
            if dataset:
                data = self.get_data( dataset )
                return trans.fill_template( "dataset/embed.mako", item=dataset, item_data=data )
        elif item_class == model.StoredWorkflow:
            workflow = self.get_stored_workflow( trans, item_id, False, True )
            workflow.annotation = self.get_item_annotation_str( trans.sa_session, workflow.user, workflow )
            if workflow:
                self.get_stored_workflow_steps( trans, workflow )
                return trans.fill_template( "workflow/embed.mako", item=workflow, item_data=workflow.latest_workflow.steps )
        elif item_class == model.Page:
            pass
        
        
        