views.Projects = Backbone.View.extend({
    el: '#project-items',
    initialize: function() {
        this.collection.on('update', this.render, this);
        $('#projects input[type="search"]').on('keyup', _.bind(this.search, this));
        
        var that = this,
            low = 50
            high = 100;
        
        $(window).on('scroll', function() {
            if  ($(window).scrollTop() == $(document).height() - $(window).height()){
                that.loadMore(low,high);
                low = high;
                high += 50;
            }
        });
    },
    loadMore: function(low,high) {
        var models = _(this.collection.filter(function(model) {
                return model.get('visible');
            })).slice(low,high);
            
        if (models.length) {
            _(models).each(function(model) {
                this.$('tbody').append(templates.project({ model: model }));
            });
        }
    },
    render: function() {

        var donor = _(app.app.filters).find(function(filter) {
                return filter.collection === 'donors';
            }),
            models = _(this.collection.filter(function(model) {
                return model.get('visible');
            })).first(50);

        // Probably should replace this with donor name
        donor = (donor) ? 1 : _(this.collection.donors).size();

        $('#total-count').html(accounting.formatNumber(this.collection.length));
        $('#total-donors').html(accounting.formatNumber(donor));
        $('#total-budget').html(accounting.formatMoney(this.collection.budget));
        $('#total-expenditure').html(accounting.formatMoney(this.collection.expenditure));

        this.$el.html(templates.projects(this));

        if (models.length) {
            _(models).each(function(model) {
                this.$('tbody').append(templates.project({ model: model }));
            });
        } else {
            this.$('tbody').append('<tr><td><em>No projects</em></td><td></td><td></td></tr>');

        }

        return this;
    },
    search: function (e) {
        var $target = $(e.target),
            val = $target.val().toLowerCase();

        this.collection.each(function(model) {
            var name = model.get('name').toLowerCase();

            if (val === '' || name.indexOf(val) >= 0) {
                model.set('visible', true);
            } else {
                model.set('visible', false);
            }
        });

        this.render();
        $('html, body').animate({
            scrollTop: $('#projects-heading').offset().top + 1
        }, 500);
    }
});
