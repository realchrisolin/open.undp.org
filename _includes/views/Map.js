views.Map = Backbone.View.extend({
    events: {
        'click img.mapmarker': 'mapClick'
    },
    initialize: function() {
        this.render();
        if (this.collection) {
            this.collection.on('update', this.render, this);
        }
    },
    render: function() {
        this.$el.empty().append('<div class="inner-shadow"></div>');
        this.buildMap();
        return this;
    },
    mapClick: function(e) {
        var $target = $(e.target);
        window.location = '#filter/operating_unit-' + $target.attr('id');
    },
    buildMap: function() {
        var that = this,
            locations = [],
            count, budget, description,
            unit = (this.collection) ? this.collection 
                : this.model.get('operating_unit_id'),
            objCheck = _.isObject(unit);

        mapbox.auto(this.el, 'mapbox.mapbox-light', function(map) {
            map.ui.zoomer.remove();
            map.ui.attribution.remove();
            map.setZoomRange(2, 17);
            
            var radii = function(f) {
                return clustr.area_to_radius(
                    Math.round(f.properties.budget / 100000)
                );
            }
            
            var markers = mapbox.markers.layer()
                .factory(clustr.scale_factory(radii, "rgba(2,56,109,0.6)", "#01386C"))
                .sort(function(a,b){ return b.properties.budget - a.properties.budget; });

            $.getJSON('api/operating-unit-index.json', function(data) {
                for (var i = 0; i < data.length; i++) {
                    var o = data[i];
                    if ((objCheck) ? unit.operating_unit[o.id] : o.id === unit) {
                    
                        if (!objCheck) { that.getregionData(o); }
                        
                        if (o.lon) {
                            (objCheck) ? count = unit.operating_unit[o.id] : count = false;
                            (objCheck) ? budget = unit.operating_unitBudget[o.id] : budget = that.model.get('budget');
                            description = '<div class="stat">Budget: <span class="value">'
                                          + accounting.formatMoney(budget) + '</span></div>';
                            if (objCheck) {
                                description += '<div class="stat">Projects: <span class="value">'
                                            + count + '</span></div>';
                            }
                            
                            locations.push({
                                geometry: {
                                    coordinates: [
                                        o.lon,
                                        o.lat
                                    ]
                                },
                                properties: {
                                    id: o.id,
                                    title: (objCheck) ? o.name : that.model.get('project_title') + '<div class="subtitle">' + o.name + '</div>',
                                    count: count,
                                    budget: budget,
                                    description: description
                                }
                            });
                        }
                    }
                }
                
                if (locations.length != 0) {
                    markers.features(locations);
                    mapbox.markers.interaction(markers);
                    map.extent(markers.extent());
                    map.addLayer(markers);
                    if (locations.length === 1) {
                        map.zoom(4);
                    }
                } else {
                    map.centerzoom({lat:20,lon:0},2);
                }
            });

        });
    },
    
    getregionData: function(data) {
        var that = this;
        _.each(['email','facebook','flickr','twitter','web'], function(v) {
            if (v) {
                //$('#webinfo').append('<p><a class="' + v + '" href="' + data[v] + '">' + data[v] + '</a></p>');
                if (v === 'twitter' && data[v]) {
                    that.twitter(data[v]);
                }
            }
        });
    },
    
    twitter: function(username) {
        var user = username.replace('@','');
        $(".tweet").tweet({
          username: user,
          avatar_size: 32,
          count: 3,
          template: "{avatar}<div>{text}</div><div class='actions'>{time} &#183; {reply_action} &#183; {retweet_action} &#183; {favorite_action}</div>",
          loading_text: "loading tweets..."
        });
        
        $('#twitter .label').append('<a href="http://twitter.com/' + user + '">' + username + '</a>');
    }
});